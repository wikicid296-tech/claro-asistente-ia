from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.clients.openai_client import get_openai_client, get_vector_store_id

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Servicio para búsqueda semántica de cursos en OpenAI Vector Store."""
    
    # Patrones regex para extraer courseId de diferentes formatos
    COURSE_ID_PATTERNS: List[Tuple[str, str]] = [
        (r'"courseId"\s*:\s*"(\d+)"', 'courseId con comillas dobles y string'),
        (r'"courseId"\s*:\s*(\d+)', 'courseId con comillas dobles'),
        (r"'courseId'\s*:\s*'(\d+)'", "courseId con comillas simples y string"),
        (r"'courseId'\s*:\s*(\d+)", "courseId con comillas simples"),
        (r'curso-(\d+)-', 'patrón curso-ID-'),
        (r'courseId\s*=\s*"(\d+)"', 'courseId con igual y comillas'),
        (r'courseId\s*=\s*(\d+)', 'courseId con igual'),
        (r'id\s*:\s*"(\d+)"', 'id con comillas dobles'),
        (r'id\s*:\s*(\d+)', 'id con dos puntos'),
        (r'"id"\s*:\s*"(\d+)"', '"id" con comillas dobles'),
        (r'"id"\s*:\s*(\d+)', '"id" sin comillas'),
        (r'ID\s*:\s*(\d+)', 'ID mayúscula'),
        (r'curso_id\s*:\s*"(\d+)"', 'curso_id con comillas'),
        (r'curso_id\s*:\s*(\d+)', 'curso_id sin comillas'),
        (r'course_id\s*:\s*"(\d+)"', 'course_id con comillas'),
        (r'course_id\s*:\s*(\d+)', 'course_id sin comillas'),
    ]
    
    # Threshold mínimo de score para considerar un resultado relevante
    MIN_SCORE_THRESHOLD: float = 0.3
    
    def __init__(self):
        self.client: Any = None
        self.vector_store_id: Optional[str] = None
    
    @staticmethod
    def get_course_name_from_catalog(course_id: str) -> str:
        """Obtiene el nombre del curso basado en el ID."""
        # Esta función es un placeholder ya que eliminamos el catálogo
        # En la implementación real, puedes obtener el nombre del cluster pack
        return f"Curso {course_id}"
    
    def _initialize_clients(self, client: Any = None, vector_store_id: Optional[str] = None) -> bool:
        """Inicializa los clientes necesarios."""
        self.client = client or get_openai_client()
        self.vector_store_id = vector_store_id or get_vector_store_id()
        
        if not self.client:
            logger.error("OpenAI client no disponible")
            return False
        if not self.vector_store_id:
            logger.error("Vector Store ID no configurado")
            return False
        
        return True
    
    @staticmethod
    def _resp_to_dict(resp: Any) -> Dict[str, Any]:
        """Convierte cualquier objeto de respuesta a dict."""
        if hasattr(resp, "to_dict"):
            return resp.to_dict()
        if hasattr(resp, "model_dump"):
            return resp.model_dump()
        return resp if isinstance(resp, dict) else {}
    
    def _extract_course_id_from_text(self, texto: str) -> Optional[str]:
        """Extrae courseId del texto usando múltiples patrones regex."""
        if not texto:
            return None
            
        for pattern, pattern_name in self.COURSE_ID_PATTERNS:
            match = re.search(pattern, texto)
            if match:
                course_id = match.group(1)
                return course_id
                
        return None
    
    def _extract_text_from_content(self, content_item: Any) -> str:
        """Extrae texto de un item de contenido."""
        content_dict = self._resp_to_dict(content_item)
        
        # Intentar diferentes campos donde podría estar el texto
        text_fields = ['text', 'content', 'value', 'data']
        
        for field in text_fields:
            if field in content_dict:
                value = content_dict[field]
                if isinstance(value, str):
                    return value
                elif value is not None:
                    return str(value)
        
        # Si tiene atributo text directamente
        if hasattr(content_item, 'text'):
            text_value = content_item.text
            if text_value:
                return str(text_value)
        
        return ""
    
    def _process_search_item(self, item: Any, idx: int, total: int, 
                           seen_ids: set, max_results: int) -> Optional[Dict[str, Any]]:
        """Procesa un item individual de la búsqueda."""
        try:
            item_dict = self._resp_to_dict(item)
            score = float(item_dict.get("score", 0) or 0)
            
            # Saltar si el score es muy bajo
            if score < self.MIN_SCORE_THRESHOLD:
                logger.debug(f"Item {idx+1} con score bajo ({score:.4f}), saltando")
                return None
            
            # Obtener contenido
            content_list = []
            if "content" in item_dict:
                content_list = item_dict["content"]
            elif hasattr(item, 'content'):
                content_list = item.content
            
            if not isinstance(content_list, list):
                return None
            
            # Buscar courseId en todo el contenido
            course_id = None
            full_text = ""
            
            for contenido in content_list:
                texto = self._extract_text_from_content(contenido)
                if texto:
                    full_text += texto + " "
                    
                    # Buscar courseId en este texto
                    if not course_id:
                        course_id = self._extract_course_id_from_text(texto)
                        if course_id:
                            break
            
            if not course_id:
                # Intentar buscar en el texto completo
                course_id = self._extract_course_id_from_text(full_text)
            
            if not course_id:
                logger.debug(f"Item {idx+1}: No se encontró courseId")
                return None
            
            # Evitar duplicados
            if course_id in seen_ids:
                logger.debug(f"Item {idx+1}: CourseId duplicado {course_id}")
                return None
            
            seen_ids.add(course_id)
            
            # Obtener nombre del curso
            course_name = self.get_course_name_from_catalog(course_id)
            if not course_name:
                course_name = "Curso disponible"
                logger.debug(f"CourseId {course_id}: No encontrado en catálogo")
            
            return {
                "courseId": course_id,
                "courseName": course_name,
                "score": score,
                "raw_text_preview": full_text[:200] + "..." if len(full_text) > 200 else full_text
            }
            
        except Exception as e:
            logger.warning(f"Error procesando item {idx+1}: {e}")
            return None
    
    def _log_search_header(self, query: str, k: int, vector_store_id: str):
        """Muestra encabezado de la búsqueda."""
        print(f"\n{'='*60}")
        print(f"🔍 BÚSQUEDA SEMÁNTICA")
        print(f"{'='*60}")
        print(f"📝 Query: '{query}'")
        print(f"🎯 Resultados máx: {k}")
        
        # Mostrar solo primeros caracteres del ID para seguridad
        if vector_store_id:
            display_id = vector_store_id[:20] + "..." if len(vector_store_id) > 20 else vector_store_id
            print(f"🔑 Vector Store: {display_id}")
        else:
            print(f"🔑 Vector Store: No configurado")
            
        print(f"📊 Threshold mínimo: {self.MIN_SCORE_THRESHOLD}")
    
    def _log_results_summary(self, results: List[Dict[str, Any]], 
                           total_items_processed: int):
        """Muestra resumen de resultados."""
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN DE RESULTADOS")
        print(f"{'='*60}")
        print(f"📈 Items procesados: {total_items_processed}")
        print(f"✅ Cursos encontrados: {len(results)}")
        
        if results:
            print(f"\n🏆 TOP RESULTADOS:")
            for i, r in enumerate(results, 1):
                name_display = r['courseName'][:50] + "..." if len(r['courseName']) > 50 else r['courseName']
                print(f"{i:2d}. ID: {r['courseId']:>6} | Score: {r['score']:.4f} | {name_display}")
        
        # Estadísticas de scores
        if results:
            scores = [r['score'] for r in results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            print(f"\n📈 ESTADÍSTICAS:")
            print(f"   • Score promedio: {avg_score:.4f}")
            print(f"   • Score máximo: {max_score:.4f}")
            print(f"   • Score mínimo: {min_score:.4f}")
            print(f"   • Rango: {max_score - min_score:.4f}")
        
        print(f"{'='*60}")
    
    def search_courses(
        self,
        query: str,
        k: int = 5,
        *,
        client: Any = None,
        vector_store_id: Optional[str] = None,
        min_score: Optional[float] = None,
        verbose: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda semántica en Vector Store de OpenAI.
        
        Args:
            query: Texto de búsqueda
            k: Número máximo de resultados a retornar
            client: Cliente de OpenAI (opcional)
            vector_store_id: ID del Vector Store (opcional)
            min_score: Score mínimo para filtrar resultados
            verbose: Si True, muestra logs detallados
            
        Returns:
            Lista de dicts con formato: [{"courseId": str, "courseName": str, "score": float}, ...]
        """
        # Validaciones iniciales
        if not query or not query.strip():
            if verbose:
                print("⚠️ Query vacío, retornando lista vacía")
            return []
        
        # Inicializar clientes
        if not self._initialize_clients(client, vector_store_id):
            return []
        
        # Verificar que tenemos vector_store_id (debería estar garantizado por _initialize_clients)
        if not self.vector_store_id:
            if verbose:
                print("❌ Vector Store ID no disponible")
            return []
        
        # Configurar threshold
        if min_score is not None:
            self.MIN_SCORE_THRESHOLD = min_score
        
        # Mostrar encabezado
        if verbose:
            self._log_search_header(query, k, self.vector_store_id)
        
        try:
            # 1. Ejecutar búsqueda en OpenAI
            if verbose:
                print("\n📤 Enviando solicitud a OpenAI...")
            
            # Usar type assertion para asegurar que no es None
            vs_id = self.vector_store_id  # Esto ya no es None porque pasó la validación
            
            response = self.client.vector_stores.search(
                vector_store_id=vs_id,
                query=query
            )
            
            if verbose:
                print("✅ Respuesta recibida")
            
            # 2. Procesar respuesta
            response_dict = self._resp_to_dict(response)
            
            # Obtener items de datos
            data_items = []
            if "data" in response_dict:
                data_items = response_dict["data"]
            elif hasattr(response, 'data'):
                data_items = response.data
            
            if not isinstance(data_items, list):
                data_items = []
            
            if verbose:
                print(f"📥 Items recibidos para procesar: {len(data_items)}")
            
            # 3. Procesar cada item
            results: List[Dict[str, Any]] = []
            seen_ids = set()
            
            for idx, item in enumerate(data_items):
                result = self._process_search_item(
                    item, idx, len(data_items), 
                    seen_ids, k
                )
                
                if result:
                    results.append(result)
                    
                    if verbose and len(results) <= 3:  # Solo log primeros 3
                        logger.info(f"✅ Encontrado: ID={result['courseId']}, "
                                  f"Score={result['score']:.4f}, "
                                  f"Name={result['courseName'][:30]}...")
                
                # Detener si ya tenemos suficientes resultados
                if len(results) >= k * 2:  # Procesamos el doble para luego filtrar
                    if verbose:
                        print(f"\n🎯 Ya tenemos {len(results)} resultados preliminares")
                    break
            
            # 4. Ordenar y filtrar
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Filtrar por threshold
            filtered_results = [
                r for r in results 
                if r["score"] >= self.MIN_SCORE_THRESHOLD
            ]
            
            # Limitar a k resultados
            final_results = filtered_results[:k]
            
            # 5. Mostrar resumen
            if verbose:
                self._log_results_summary(final_results, len(data_items))
            
            # Log final
            if final_results:
                logger.info(
                    f"Búsqueda completada: query='{query}', "
                    f"encontrados={len(final_results)}, "
                    f"top_score={final_results[0]['score']:.4f}"
                )
            else:
                logger.info(f"Búsqueda completada: query='{query}', sin resultados")
            
            return final_results
            
        except Exception as e:
            error_msg = f"Error en búsqueda semántica: {e}"
            if verbose:
                print(f"\n❌ ERROR: {error_msg}")
            logger.error(error_msg, exc_info=True)
            return []


# Función de conveniencia para mantener compatibilidad
def search_aprende_courses(
    query: str,
    k: int = 5,
    *,
    client: Any = None,
    vector_store_id: Optional[str] = None,
    min_score: Optional[float] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Función de conveniencia para búsqueda de cursos.
    Mantiene compatibilidad con código existente.
    """
    service = SemanticSearchService()
    return service.search_courses(
        query=query,
        k=k,
        client=client,
        vector_store_id=vector_store_id,
        min_score=min_score,
        verbose=verbose
    )