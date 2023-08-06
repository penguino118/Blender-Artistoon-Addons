# Blender Artistoon Model Addons
Blender scripts to manage model files from the Artistoon engine. Only tested with [**GioGio's Bizarre Adventure (PS2)**](https://jojowiki.com/GioGio%27s_Bizarre_Adventure).<br>

## Exporter To-Do
- Find better solution for Triangle Strips
- Add more material and attribute types
- Separate textures from materials
- Use material type custom properties whenever possible
- Export collision data sectors (`11000000`) if found
- Use per-object attributes from the import script whenever possible

## Importer To-Do
- Add more material types
- Figure out unknown attribute flags
- Read collision data sectors (`11000000`)
- Add material type as a custom property for the exporter
