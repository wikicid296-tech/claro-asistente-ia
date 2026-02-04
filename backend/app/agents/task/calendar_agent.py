from __future__ import annotations
from typing import Dict, Any

from app.services.datetime_normalizer_service import normalize_datetime_from_text
from app.services.calendar_ics import crear_invitacion_ics


class CalendarTaskAgent:
    """
    Agente de eventos de calendario (DEBUG).

    Responsabilidades:
    - NO pregunta directamente
    - NO inventa datos
    - Señala carencias reales (fecha / hora / link)
    """

    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        print("\n================ CALENDAR TASK AGENT ================")
        print("📥 CONTENT:")
        print(content)

        print("\n📥 ANALYSIS RAW:")
        print(analysis)

        # -------------------------------------------------
        # 1) Detectar carencias desde analysis
        # -------------------------------------------------
        missing_fields = analysis.get("missing_fields", []) or []
        missing = set(missing_fields)

        print("\n🔎 MISSING FIELDS:")
        print(missing)

        needs_meeting_link = "meeting_link" in missing

        fecha_from_analysis = analysis.get("fecha")
        hora_from_analysis = analysis.get("hora")

        print("\n🕒 FECHA / HORA DESDE ANALYSIS:")
        print("fecha:", fecha_from_analysis)
        print("hora :", hora_from_analysis)

        # Regla correcta: fecha Y hora son obligatorias
        needs_datetime = not (fecha_from_analysis and hora_from_analysis)

        print("\n❓ NEEDS DATETIME?:", needs_datetime)

        enrichment_candidates: list[str] = []

        if needs_meeting_link:
            enrichment_candidates.append("meeting_link")

        if needs_datetime:
            enrichment_candidates.append("datetime")

        print("\n✨ ENRICHMENT CANDIDATES:")
        print(enrichment_candidates)

        # -------------------------------------------------
        # 2) Normalización FASE 8 (solo si no faltan datos)
        # -------------------------------------------------
        fecha: str | None = fecha_from_analysis
        hora: str | None = hora_from_analysis
        ics: str | None = None

        if not needs_datetime:
            print("\n🛠️ NORMALIZING DATETIME FROM CONTENT...")
            dt = normalize_datetime_from_text(text=content)
            print("➡️ normalize_datetime_from_text output:", dt)

            fecha = dt.get("fecha")
            hora = dt.get("hora")

            print("✅ NORMALIZED:")
            print("fecha:", fecha)
            print("hora :", hora)

            # ---------------------------------------------
            # 3) Generación de ICS
            # ---------------------------------------------
            if fecha and hora:
                try:
                    print("\n📆 GENERATING ICS...")
                    ics = crear_invitacion_ics(
                        titulo=content,
                        descripcion=content,
                        fecha=fecha,
                        hora=hora,
                    )
                    print("✅ ICS GENERATED (length):", len(ics))
                except Exception as e:
                    print("❌ ERROR GENERATING ICS:", e)
                    ics = None
            else:
                print("\n⚠️ ICS NOT GENERATED (missing fecha or hora)")

        else:
            print("\n⏭️ SKIPPING NORMALIZATION & ICS (needs follow-up)")

        result = {
            "task_type": "calendar",
            "status": "created",
            "content": content,

            "fecha": fecha,
            "hora": hora,
            "ics": ics,

            "enrichment_candidates": enrichment_candidates,
            "needs_followup": bool(enrichment_candidates),
            "followup_question": None,
        }

        print("\n📤 FINAL RESULT:")
        print(result)
        print("================ END CALENDAR TASK AGENT ================\n")

        return result
