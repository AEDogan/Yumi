"""Keep transport alive while exclusively leasing the mic only during a conversation."""
import asyncio,time
from idle_timeout import IdleTimeout

async def serve(session,args,stop,controls,feedback,device_factory,lease_factory,pressure):
    device=None;sender=None;lease=None;listening=False;idle=IdleTimeout(seconds=4)
    end=time.monotonic()+args.seconds if args.seconds else float('inf')
    async def release():
        nonlocal device,sender,lease,listening
        # Retire ownership first so a second cleanup cannot close the same
        # failed device again or leave its microphone lease behind.
        old_sender,old_device,old_lease=sender,device,lease
        sender=device=lease=None;listening=False
        try:
            if old_sender:
                old_sender.cancel();await asyncio.gather(old_sender,return_exceptions=True)
        finally:
            try:
                if old_device:old_device.close()
            finally:
                if old_lease:old_lease.close()
    async def open_device(capture):
        nonlocal device,sender,lease,listening,idle
        await release()
        if capture:lease=lease_factory()
        device=device_factory(session,args.input_device,args.output_device,capture_enabled=capture)
        await device.open();device.start()
        if capture:
            sender=asyncio.create_task(device.send());listening=True;idle=IdleTimeout(seconds=4)
            session.emit('listening')
    receiver=asyncio.create_task(session.receive())
    try:
        session.emit('standby')
        if not getattr(args,'standby',False):await open_device(True)
        had_audio=False
        while not stop.is_set() and time.monotonic()<end:
            if receiver.done():receiver.result();return
            if sender and sender.done():sender.result();raise RuntimeError('Audio sender stopped')
            if device and device.failure:raise RuntimeError(device.failure)
            if pressure():raise RuntimeError('Ses oturumu için kullanılabilir bellek azaldı.')
            while not controls.empty():
                command=controls.get_nowait()
                if command=='activate' and not listening:
                    await open_device(True)
                elif command=='deactivate':
                    captured=listening
                    await release()
                    if captured:await session.end_audio()
                    session.flush('conversation_paused');session.emit('standby')
            if not feedback.pending.empty() and device is None:await open_device(False)
            await feedback.pump(session)
            if device is None and not getattr(session,'skill_feedback_active',False):
                # A response already in flight when the user closes the mic
                # must not accumulate and play on the next conversation.
                session.playback.clear()
            queued=bool(len(session.playback))
            if had_audio and not queued:session.emit('playback_drained')
            had_audio=queued
            if listening and idle.expired(session):
                await release();await session.end_audio();session.emit('standby')
            if device and not listening and feedback.pending.empty() and not getattr(session,'skill_feedback_active',False) and not queued and not session.generating and time.monotonic()-session.last_played>.20:
                await release()
            await asyncio.sleep(.05)
    finally:
        try:await release()
        finally:
            receiver.cancel();await asyncio.gather(receiver,return_exceptions=True)
