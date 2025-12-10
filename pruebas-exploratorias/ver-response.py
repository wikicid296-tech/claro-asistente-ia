from openai import OpenAI

OPENAI_API_KEY = ""
VECTOR_STORE_ID = ""

client = OpenAI(api_key=OPENAI_API_KEY)

def imprimir_respuesta_raw(query: str = "python"):
    """
    Imprime la respuesta raw de OpenAI sin intentar acceder a nada
    """
    print("=" * 80)
    print("🛠️  IMPRIMIENDO RESPUESTA RAW DE OPENAI")
    print("=" * 80)
    
    try:
        print(f"\n📤 Enviando consulta: '{query}'")
        

        resp = client.vector_stores.search(
            vector_store_id=VECTOR_STORE_ID,
            query=query
        )
        
        print(f"\n✅ Respuesta recibida:")
        print(f"🔍 Tipo completo: {type(resp)}")
        print(f"🔍 Representación string: {resp}")
        
        print("\n" + "=" * 80)
        print("📦 CONTENIDO COMPLETO DE LA RESPUESTA:")
        print("=" * 80)
        

        print("\n1️⃣ Como string:")
        print("-" * 40)
        print(str(resp))
        
        print("\n" + "=" * 80)
        

        print("\n2️⃣ Probando si es iterable:")
        print("-" * 40)
        try:
            print(f"¿Se puede iterar? {hasattr(resp, '__iter__')}")
            if hasattr(resp, '__iter__'):
                print("Intentando iterar...")
                for i, item in enumerate(resp):
                    print(f"\n  Item {i}:")
                    print(f"    Tipo: {type(item)}")
                    print(f"    String: {item}")
                    print(f"    Dir: {[x for x in dir(item) if not x.startswith('_')][:10]}...")
                    
                    # Cortar después de 3 items
                    if i >= 2:
                        print(f"    ... y más items")
                        break
        except Exception as e:
            print(f"Error al iterar: {e}")
        
        print("\n" + "=" * 80)
        
        print("\n3️⃣ Atributos del objeto respuesta:")
        print("-" * 40)
        attrs = [attr for attr in dir(resp) if not attr.startswith('_')]
        for attr in attrs:
            try:
                valor = getattr(resp, attr)
                print(f"  {attr}: {type(valor)} = {repr(valor)[:100]}")
            except:
                print(f"  {attr}: ERROR al acceder")
        
        print("\n" + "=" * 80)
        

        print("\n4️⃣ Intentando métodos específicos:")
        print("-" * 40)
        

        if hasattr(resp, 'to_dict'):
            print("Tiene método to_dict()")
            try:
                dict_resp = resp.to_dict()
                print(f"to_dict() result: {dict_resp}")
            except Exception as e:
                print(f"Error en to_dict(): {e}")
        else:
            print("NO tiene método to_dict()")
        

        if hasattr(resp, '__dict__'):
            print("\nTiene __dict__:")
            for key, value in resp.__dict__.items():
                print(f"  {key}: {type(value)} = {repr(value)[:80]}")
        
        print("\n" + "=" * 80)

        print("\n5️⃣ Intentando exportar a formato JSON:")
        print("-" * 40)
        try:
            import json
            

            if hasattr(resp, 'model_dump'):
                print("Usando model_dump():")
                data = resp.model_dump()
                print(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:500])
            
            # Si tiene dict (Pydantic v1)
            elif hasattr(resp, 'dict'):
                print("Usando dict():")
                data = resp.dict()
                print(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:500])
            
            else:
                print("No se encontraron métodos de serialización conocidos")
                
        except Exception as e:
            print(f"Error al exportar JSON: {e}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error en la consulta: {e}")
        import traceback
        print("\n🔍 Traceback completo:")
        traceback.print_exc()


def imprimir_super_simple(query: str = "python"):
    """
    La versión más simple posible - solo imprime
    """
    print("\n" + "=" * 80)
    print("🚀 IMPRESIÓN SUPER SIMPLE")
    print("=" * 80)
    
    resp = client.vector_stores.search(
        vector_store_id=VECTOR_STORE_ID,
        query=query
    )
    
    print("\n📦 LA RESPUESTA ES:")
    print("-" * 40)
    print(resp)
    
    print("\n🔍 Y SU TIPO ES:")
    print("-" * 40)
    print(type(resp))
    
    print("\n📝 Y SE VE ASÍ AL IMPRIMIRLO:")
    print("-" * 40)
    print(repr(resp))

if __name__ == "__main__":
    print("¿Cómo quieres ver la respuesta?")
    print("1. Imprimir todo (completo)")
    print("2. Solo lo básico (super simple)")
    
    opcion = input("\nElige opción (1 o 2): ").strip()
    
    consulta = input("Consulta a buscar (o Enter para 'python'): ").strip()
    if not consulta:
        consulta = "python"
    
    if opcion == "2":
        imprimir_super_simple(consulta)
    else:
        imprimir_respuesta_raw(consulta)
    
    print("\n🎯 Con esta información ya podemos ver EXACTAMENTE qué devuelve OpenAI")