# Ses oturumu dar haritası

Ana başlangıç ../DURUM.md. Bu harita 26 Ekim ses toparlama paketi içindir; tüm klasörü tarama.

- live_core.py: connect, receive, _closed, is_quiet, maybe_resume, resume, close. Kurulum iptali, eski soket mesajı ve kaynak temizliği burada.
- persistent_audio.py: serve/release/open_device; mikrofon lease, gönderici/alıcı ve aygıt yaşam döngüsü.
- provider_errors.py: güvenli hata kategorileri; 1008 tek başına kota değildir.
- idle_timeout.py: konuşma/yanıt/araç/oynatma sırasında boşta kapanmayı engeller.
- browser_audio.py ve microphone_lease.py: gerçek aygıt/Qt ve tek mikrofon kilidi.
- run_live.py: işçi giriş noktası ve güvenli tanısal kayıtlar.
- ../native_live.py ve ../app.py: yalnız yeniden bağlanma arayüzü/işçi sahipliği gerektiğinde ilgili metodları oku.
- ../work/check_live_cleanup_failures.py, check_live_reconnect_races.py, check_live_resume_tail.py, check_live_resume_quiet.py, check_provider_errors.py: odaklı ağsız kontroller.
- ../work/check_persistent_voice.py, check_skill_feedback.py, check_native_recovery.py, check_voice_worker_cleanup.py: yaşam döngüsü ve geçici UI/işçi kabulü.
- ../work/check_live_long_session.py: gerçek sağlayıcıyla 3700 saniye, mikrofon/hoparlör ve kayıtlı sohbet olmadan uzun bağlantı testi. Ücretli/gerçek servis denemesi olduğunu doğru raporla; yerel test yerine geçmez.

Son kabul: `../docs/SES-SONUC-2026-10-26.md`; uzun test başarısız, kontrollü gerçek resume geçti.
