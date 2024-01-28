# Blender Artistoon Addons
Blender scripts to manage model files from the Artistoon engine. Only tested with [**GioGio's Bizarre Adventure (PS2)**](https://jojowiki.com/GioGio%27s_Bizarre_Adventure).<br>

## Model Importer (AMO)
### To-do
- Figure out unknown attribute flags
- Support Auto Modellista meshes...?

## Armature Importer (AHI)
### To-do
- Figure out unknown attribute flags

## Animation Importer (AAN)
### To-do
- Test on more files
- Set frame range and loop start values when creating animation actions
- Probably use FCurve 'Ease In' and 'Ease Out' values for something

## Model Exporter (AMO)
### To-do
- Find better solution for Triangle Strips
  - Current solution is unnefficient and ocasionally messes up list order while handling multiple materials.

## Armature Exporter (AHI)
### To-do
- Rotation isn't always correct (?)
  - Rotation is ocasionally missing for some bones on export, not sure why.
