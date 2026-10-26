# Yumi_skins — Dosya / Kod Haritası

Üretim: 2026-10-23. Dosya adlarından türetilmiştir; işlevsel analiz değildir.
Amaç: ilgili dizini seç, dar arama yap, yalnız gerekli kod aralıklarını oku.

## Başlangıç ve yapılandırma

- `Yumi_skins.uproject`

## Dizin → örnek kaynak yolları

- **`Config/`**: `Config/DefaultEditor.ini`, `Config/DefaultEditorPerProjectUserSettings.ini`, `Config/DefaultEngine.ini`, `Config/DefaultGame.ini`, `Config/DefaultInput.ini`, `Config/Localization/Game_Compile.ini`, `Config/Localization/Game_Export.ini`, `Config/Localization/Game_ExportDialogueScript.ini`, `Config/Localization/Game_Gather.ini`, `Config/Localization/Game_GenerateReports.ini`, `Config/Localization/Game_Import.ini`, `Config/Localization/Game_ImportDialogue.ini`
  - Liste örnektir; bu dizinin kalan dosyalarını gerektiğinde `rg --files` ile daralt.
- **`Content/`**: `Content/FirstPerson/Lvl_FirstPerson.ini`

## Arama sınırları

- Dizin örnekleri tam envanter değildir. Önce ilgili yolu doğrula; bulunamazsa kapsamı adım adım genişlet.
- Sırlar ve dosya içerikleri okunmadı. Üretilmiş dosyalar/bağımlılıklar varsayılan keşfe dahil edilmedi.
- Güncelleme: önemli yapı değişikliğinde ilgili kaydı düzenle; toplu yenileme aracını her görevde çalıştırma.
- Varsayılan kapsam dışı kök dizinler: `DerivedDataCache/`, `Intermediate/`, `Saved/`
