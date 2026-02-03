from app.services.cerebro_service import procesar_chat_web


def test_descubre_triggers_llm_and_task(monkeypatch):
    # Mock classifier to return task/reminder
    monkeypatch.setattr(
        'app.services.intent_clasification_service.classify_intent',
        lambda message: {"macro_intent": "task", "task_type": "reminder"}
    )

    # Mock state loader
    class DummyState:
        intent = None
        awaiting_slot = None
        slots = {}

    monkeypatch.setattr('app.services.cerebro_service.load_state', lambda user_key: DummyState())

    # Mock the task orchestrator to capture the task type and return a task action
    called = {}

    def fake_handle_task_web(user_message, normalized, ttype, state):
        called['ttype'] = ttype
        return {"action": "task", "task": {"task_type": ttype, "content": normalized}}

    monkeypatch.setattr('app.services.cerebro_service.handle_task_web', fake_handle_task_web)

    res = procesar_chat_web(
        user_message='recuérdame bajar la ropa a las 5pm',
        action='descubre',
        user_key='test_session',
        macro_intent=None,
        task_type=None,
    )

    assert res.get('action') == 'task'
    assert called.get('ttype') == 'reminder'
