from typing import List
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from rdkit import Chem, Geometry
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem import Draw, rdDepictor

"""
Use rdkit to draw molecule. Higher uncertainty results in red marks.
"""

class MoleculeDrawer():
  @staticmethod
  def _get_similarity_map_from_weights(mol, weights, colorMap=None, sigma=None,
                                  contourLines=10, draw2d=None, unc_type=None, **kwargs):
    """
  从 Chem.Draw.SimilarityMaps 的 GetSimilarityMapFromWeights 函数复制而来

  根据原子权重为分子生成相似性映射图。

  参数：
    mol -- 目标分子
    colorMap -- 采用的 matplotlib 色彩图方案，默认是自定义的 PiWG 色彩图
    sigma -- 高斯分布的 sigma 值
    contourLines -- 如果是整数 N：绘制 N 条等高线；如果是一个数字列表：在这些数字对应的值上绘制等高线
    alpha -- 等高线的透明度（alpha 混合值）
    unc_type -- 如果是 'pred'，则不在原子上绘制颜色
    kwargs -- 绘图时的其他附加参数
      """
    if mol.GetNumAtoms() < 2:
      raise ValueError("too few atoms")

    if draw2d is not None:
      mol = rdMolDraw2D.PrepareMolForDrawing(mol, addChiralHs=False)
      if not mol.GetNumConformers():
        rdDepictor.Compute2DCoords(mol)
      if sigma is None:
        if mol.GetNumBonds() > 0:
          bond = mol.GetBondWithIdx(0)
          idx1 = bond.GetBeginAtomIdx()
          idx2 = bond.GetEndAtomIdx()
          sigma = 0.3 * (mol.GetConformer().GetAtomPosition(idx1) -
                        mol.GetConformer().GetAtomPosition(idx2)).Length()
        else:
          sigma = 0.3 * (mol.GetConformer().GetAtomPosition(0) -
                        mol.GetConformer().GetAtomPosition(1)).Length()
        sigma = round(sigma, 2)

      sigmas = [sigma] * mol.GetNumAtoms()
      locs = []
      max_atom_pos_y = 0
      for i in range(mol.GetNumAtoms()):
        p = mol.GetConformer().GetAtomPosition(i)
        locs.append(Geometry.Point2D(p.x, p.y))
        max_atom_pos_y = p.y if p.y > max_atom_pos_y else max_atom_pos_y
      
      if unc_type == 'pred':
        draw2d.DrawMolecule(mol) 
        return None, max_atom_pos_y

      draw2d.ClearDrawing()
      ps = Draw.ContourParams()
      ps.fillGrid = True
      ps.gridResolution = 0.03
      ps.extraGridPadding = 0.5

      if colorMap is not None:
        if cm is not None and isinstance(colorMap, type(cm.Blues)):
          # it's a matplotlib colormap:
          clrs = [tuple(x) for x in colorMap([0, 0.5, 1])]
        elif type(colorMap) == str:
          if cm is None:
            raise ValueError("cannot provide named colormaps unless matplotlib is installed")
          clrs = [tuple(x) for x in cm.get_cmap(colorMap)([0, 0.5, 1])]
        else:
          clrs = [colorMap[0], colorMap[1], colorMap[2]]
        ps.setColourMap(clrs)

      Draw.ContourAndDrawGaussians(draw2d, locs, weights, sigmas, nContours=contourLines, params=ps)
      draw2d.drawOptions().clearBackground = False
      draw2d.DrawMolecule(mol) 
      return draw2d, max_atom_pos_y

  @staticmethod
  def draw_molecule_with_atom_notes(smiles: str, mol_note: float, atom_notes: List, unc_type: str, svg: bool=True):
      draw_opts = rdMolDraw2D.MolDrawOptions()
      draw_opts.addAtomIndices = False  # We don't want to show default atom indices
      draw_opts.atomNoteFontSize = 16  # Set the font size for atom notes

      colors = [(1, 0.2, 0.2), (1, 1, 1), (1, 0.2, 0.2)] # pink
      cmap = LinearSegmentedColormap.from_list('self_define', colors, N=100)
      mol = Chem.MolFromSmiles(smiles)

      atom_notes = list(atom_notes[:mol.GetNumHeavyAtoms()])

      if svg:
          drawer = rdMolDraw2D.MolDraw2DSVG(520, 550)  # Set the size of the drawing
      else:
          drawer = rdMolDraw2D.MolDraw2DCairo(520, 550)  # Specify the desired image size
          
      drawer.SetDrawOptions(draw_opts)
      for atom, note in zip(mol.GetAtoms(), atom_notes):
          atom.SetProp('atomNote', str(note))
          atom.SetProp('atomLabel', atom.GetSymbol()) # forces all atoms, including carbons, to be labeled with their element symbols

      _, max_atom_pos_y = MoleculeDrawer._get_similarity_map_from_weights(mol, atom_notes, colorMap=cmap, contourLines=2, draw2d=drawer, alpha=3, sigma=0.25, unc_type=unc_type) #0.34
      max_atom_pos_y = max_atom_pos_y*1.7

      if unc_type == 'pred':
          drawer.DrawString(f'Prediction: {mol_note:.2f}', Geometry.Point2D(0, max_atom_pos_y))
      
      elif unc_type == 'ale':
          drawer.DrawString(f'Aleatoric: {mol_note:.2f}', Geometry.Point2D(0, max_atom_pos_y))
      elif unc_type == 'epi':
          drawer.DrawString(f'Epistemic: {mol_note:.2f}', Geometry.Point2D(0, max_atom_pos_y))
      else:
          drawer.DrawString(f'Total: {mol_note:.2f}', Geometry.Point2D(0, max_atom_pos_y)) 

      drawer.FinishDrawing()
      svg = drawer.GetDrawingText()
      return svg
