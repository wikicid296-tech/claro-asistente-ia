from agents.telcel.telcel_agent import TelcelAgent


def handle_telcel_intent(user_message: str, context: dict) -> dict:
    """
    Maneja el intent Telcel delegando la respuesta al TelcelAgent.
    """
    agent = TelcelAgent(
        user_message=user_message,
        context=context,
        intent="telcel"
    )

    return agent.handle()
