from app.services.capture_service import CaptureService


async def test_capture_trims_and_lists(db, test_user):
    svc = CaptureService(db)
    cap = await svc.create(test_user.id, "  comprar leite  ")
    assert cap.content == "comprar leite"
    inbox = await svc.get_inbox(test_user.id)
    assert len(inbox) == 1


async def test_process_capture_as_task(db, test_user):
    svc = CaptureService(db)
    cap = await svc.create(test_user.id, "comprar leite")
    capture, task = await svc.process_as_task(
        cap.id, test_user.id, title="Comprar leite", importancia=3.0
    )
    assert task.title == "Comprar leite"
    assert task.importancia == 3.0
    assert task.sem_nota is False
    # Sai da caixa de entrada após processar.
    inbox = await svc.get_inbox(test_user.id)
    assert len(inbox) == 0


async def test_discard_to_trash_then_restore(db, test_user):
    svc = CaptureService(db)
    cap = await svc.create(test_user.id, "ideia solta")
    await svc.discard_to_trash(cap.id, test_user.id)
    assert len(await svc.get_inbox(test_user.id)) == 0
    assert len(await svc.get_trash(test_user.id)) == 1
    await svc.restore(cap.id, test_user.id)
    assert len(await svc.get_inbox(test_user.id)) == 1
