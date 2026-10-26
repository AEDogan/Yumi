# Yumi — Dosya / Kod Haritası

Üretim: 2026-10-23. Dosya adlarından türetilmiştir; işlevsel analiz değildir.
Amaç: ilgili dizini seç, dar arama yap, yalnız gerekli kod aralıklarını oku.

Üretim anındaki HEAD: `48798ff` (çalışma ağacındaki değişiklikler dahil değildir).

## Başlangıç ve yapılandırma

- `action_transition.py`
- `aist_dance.py`
- `api.py`
- `app.py`
- `app_paths.py`
- `async_mask.py`
- `audio_devices.py`
- `avatar.py`
- `avatar_commands.py`
- `backend.py`
- `book_contacts.py`
- `browser_chat.py`
- `captured_dance.py`
- `cat_motion.py`
- `character_names.py`
- `chat_store.py`
- `clippy_character.py`
- `coffee_scene.py`
- `contact_physics.py`
- `conversation_motion.py`
- `cup_grip.py`
- `daily_scenarios.py`
- `dance_contacts.py`
- `dance_motion.py`
- `dance_repertoire.py`
- `dance_styles.py`
- `desktop_vrm.py`
- `seated_garment.py`: otururken hip askılı ön etek panelinin geçici çizim düzeltmesi
- `DURUM.md`
- `finger_contacts.py`
- `fullscreen_pause.py`
- `furniture_contacts.py`
- `furniture_scene.py`
- `gait.py`
- `garment_contacts.py`
- `gemini_api.py`
- `gemini_chat.py`
- `genre_dance.py`
- `grip_surface.py`
- `grounding.py`
- `hand_pose.py`
- `interaction_ik.py`
- `item_assets.py`
- `item_contacts.py`
- `joint_limits.py`
- `keyword_detector.py`
- `launch.py`
- `live_history.py`
- `locomotion.py`
- `media_activity.py`
- `model_analysis.py`
- `model_compatibility.py`
- `model_setup.py`
- `model_visibility.py`
- `motion.py`
- `motion_space.py`
- `motion_ui.py`
- `music_analysis.py`
- `music_clock.py`
- `music_genre.py`
- `music_runtime.py`
- `native_live.py`
- `native_transcripts.py`
- `native_wake.py`
- `motion_reference.py`: Paket metadatasıyla açılan kaynak kol referansı; mevcut modellerin bind geometrisini değiştirmeden A/T poz uyarlaması.
- `natural_walk.py`
- `overlay.py`
- Diğer 47 kök dosyası: gerektiğinde kökte dosya adı filtresiyle ara.

## Dizin → örnek kaynak yolları

- **`assets/`**: `assets/characters/manifest.json`, `assets/clippy/agent.json`, `assets/manifest.json`
- **`items/`**: `items/alternatives/manifest.json`, `items/manifest-seats-v1-backup.json`, `items/manifest.json`, `items/SOURCES_AND_LICENSES.json`
- **`live_voice/`**: `live_voice/audio.html`, `live_voice/audio_worklet.js`, `live_voice/browser_audio.py`, `live_voice/contracts.py`, `live_voice/idle_timeout.py`, `live_voice/live_core.py`, `live_voice/microphone_lease.py`, `live_voice/persistent_audio.py`, `live_voice/provider_errors.py`, `live_voice/run_live.py`, `live_voice/skill_feedback.py`, `live_voice/transcript_turns.py`
  - Liste örnektir; bu dizinin kalan dosyalarını gerektiğinde `rg --files` ile daralt.
- **`vrm_runtime/`**: `vrm_runtime/package-lock.json`, `vrm_runtime/package.json`, `vrm_runtime/viewer.html`
- **`yumi_skills/`**: `yumi_skills/__init__.py`, `yumi_skills/android_tv_bridge.py`, `yumi_skills/dispatcher.py`, `yumi_skills/engine.py`, `yumi_skills/skills/__init__.py`, `yumi_skills/skills/briefing_skill.py`, `yumi_skills/skills/calendar_skill.py`, `yumi_skills/skills/lifestyle_cooking_skill.py`, `yumi_skills/skills/list_memory_skill.py`, `yumi_skills/skills/media_system_skill.py`, `yumi_skills/skills/routine_skill.py`, `yumi_skills/skills/smart_home_skill.py`
  - Liste örnektir; bu dizinin kalan dosyalarını gerektiğinde `rg --files` ile daralt.
- **`Yumi_skins/`**: `Yumi_skins/Config/DefaultEditor.ini`, `Yumi_skins/Config/DefaultEditorPerProjectUserSettings.ini`, `Yumi_skins/Config/DefaultEngine.ini`, `Yumi_skins/Config/DefaultGame.ini`, `Yumi_skins/Config/DefaultInput.ini`, `Yumi_skins/Config/Localization/Game_Compile.ini`, `Yumi_skins/Config/Localization/Game_Export.ini`, `Yumi_skins/Config/Localization/Game_ExportDialogueScript.ini`, `Yumi_skins/Config/Localization/Game_Gather.ini`, `Yumi_skins/Config/Localization/Game_GenerateReports.ini`, `Yumi_skins/Config/Localization/Game_Import.ini`, `Yumi_skins/Config/Localization/Game_ImportDialogue.ini`
  - Liste örnektir; bu dizinin kalan dosyalarını gerektiğinde `rg --files` ile daralt.

## Arama sınırları

- Dizin örnekleri tam envanter değildir. Önce ilgili yolu doğrula; bulunamazsa kapsamı adım adım genişlet.
- Sırlar ve dosya içerikleri okunmadı. Üretilmiş dosyalar/bağımlılıklar varsayılan keşfe dahil edilmedi.
- Güncelleme: önemli yapı değişikliğinde ilgili kaydı düzenle; toplu yenileme aracını her görevde çalıştırma.
- Varsayılan kapsam dışı kök dizinler: `.agents/`, `.git/`, `.venv/`, `__pycache__/`, `models/`, `motions/`, `outputs/`, `skins/`, `work/`


- `model_packages.py`: imzalı .yumimodel doğrulama/kurulum; `publish_model_package.py`: yalnız yayıncı paketleme aracı.
- Model paket grupları: `skins.py` (`grouped_available`, `package_group`); seçim arayüzleri `app.py` ve `overlay.py`; imzalı grup alanı `model_packages.py`; yayıncı `publish_model_package.py --group`.

- `facial_defaults.py`: yalnız modelin açık extras.yumi.defaultExpressions verisiyle nötr yüz katmanı; blink artık değerleriyle birleşir.


## 26 Ekim düzenleme ve hızlı devam
- `docs/DEVIR-2026-10-26.md`: sıralı kalan işler, doğrulama ve sıradaki tek paket.
- `docs/archive/DURUM-before-2026-10-26-checkpoint.md`: önceki ayrıntılı durum; başlangıçta topluca okuma.
- `related-projects/yumi_skills-standalone/`: eski C:/Projeler/yumi_skills ayrı kopyası. Aktif Python paketi mevcut `yumi_skills/` altında.
- `related-projects/Yumi_skins-standalone/`: eski C:/Projeler/Yumi_skins ayrı Unreal kopyası. Mevcut `Yumi_skins/` ile birleştirilmedi.
- Ses boşta/yenileme: `live_voice/live_core.py:is_quiet/maybe_resume/_closed`; `work/check_live_resume_tail.py`, `work/check_live_resume_quiet.py`, `work/check_provider_errors.py`.


## Ses ve senaryo devam yolları — 26 Ekim
- `live_voice/CODEBASE_MAP.md`: ses bağlantısı, aygıt/lease temizliği, yenileme ve hata kategorileri.
- `daily_scenarios.py`: seçim/komut kuyruğu ve yapıcı hata geri dönüşü; `furniture_scene.py:request_exit`: erken iptal/geri yürüyüş; `scenario_activity.py`: kullanılmamış senaryo iptali ve fiziksel eşya temizliği.
- `work/check_live_cleanup_failures.py`, `work/check_live_reconnect_races.py`: iptal, kapanış ve eski soket yarışları.
- `work/check_scenario_lifecycle.py`, `work/check_scenario_early_cancel.py`, `work/check_scenario_real_cancel.py`, `work/render_scenario_cancel.py`: komut/hata/erken iptal/gerçek çizici kontrolleri.
- `docs/SENARYOLAR-2026-10-26.md`: 3. başlık sonuç ve sınırlar; `docs/CIHAZ-BAGLANTISI-ARASTIRMA.md`: API anahtarı yerine hesap/QR/kod akışları için araştırma ve yapılacaklar.
- `yumi_skills/CODEBASE_MAP.md`: aktif akıllı ev modülü dar haritası. `docs/ERTELENEN-SKIN-ISLERI-2026-10-26.md`: ertelenen görünüm ve Witcher karakter sesleri.

- Son ses test sonucu ve açık uzun kabul: `docs/SES-SONUC-2026-10-26.md`.
