"""Import only signed Yumi model packages; preview remains available separately."""
def import_models(owner,paths,completed=None):
 if not paths or owner.pages.busy:return
 from model_packages import install_package
 from voice_profiles import profile
 from app import save_settings
 keys=[]
 for path in paths:
  try:
   key=install_package(path)
   owner.settings.setdefault('voice_profiles',{})[key]=profile(owner.settings,key)
   save_settings(owner.settings);keys.append(key)
  except Exception as error:owner.show_error(str(error))
 if completed:completed(keys)
