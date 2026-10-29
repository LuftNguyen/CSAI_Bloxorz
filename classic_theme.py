"""Classic presentation only: original textures, stone slabs and aged metal."""
from pathlib import Path
from copy import deepcopy
from math import tan, radians
from ursina import Entity, Mesh, Vec3, Text, Button, Texture, camera, color, scene
from ursina.shaders import lit_with_shadows_shader, unlit_shader
from gameModel.board import Tile

ASSETS = Path(__file__).resolve().parent / 'assets/classic'
INK = color.hex('#241108')
GOLD = color.hex('#ecc391')
MUTED = color.hex('#c39368')


def set_block_pose(mesh, position, scale, *, preserve_faces=False):
    """Normalize the motion frame without turning the textured faces back."""
    parts = getattr(mesh, '_visual_parts', ())
    world = [part.get_mat(scene) for part in parts] if preserve_faces else None
    mesh.rotation = (0, 0, 0)
    mesh.position = position
    mesh.scale = scale
    if world is not None:
        for part, matrix in zip(parts, world):
            part.set_mat(scene, matrix)
    else:
        for part, transform in zip(parts, getattr(mesh, '_visual_rest', ())):
            part.set_transform(transform)


def bronze_button(parent, text, y, callback, x=0, width=.32):
    b = Button(parent=parent, text=text, model='quad',
               texture=Texture(ASSETS/'bronze_button.png'),
               position=(x,y), scale=(width,.058), color=color.white,
               text_color=INK, highlight_color=color.hex('#ffe1b0'),
               pressed_color=color.hex('#ac7245'), on_click=callback)
    b.text_entity.font = 'VeraMono.ttf'
    return b


def panel(parent, title, height=.66):
    Entity(parent=parent, model='quad', scale=(.68,height), y=-.018, z=1.2,
           color=color.rgba(0,0,0,.55))
    Entity(parent=parent, model='quad', scale=(.65,height), z=1,
           color=color.hex('#9f6638'))
    Entity(parent=parent, model='quad', scale=(.635,height-.016), z=.9,
           color=color.hex('#321409'))
    return Text(parent=parent, text=title, origin=(0,0), y=height/2-.09,
                scale=2.2, color=GOLD, font='VeraMono.ttf')


def slab_mesh():
    vertices, triangles, uvs, colors, normals = [], [], [], [], []
    def quad(points, shade):
        start = len(vertices)
        normal = (Vec3(*points[1])-Vec3(*points[0])).cross(Vec3(*points[2])-Vec3(*points[0])).normalized()
        vertices.extend(points)
        triangles.extend([(start,start+1,start+2),(start,start+2,start+3)])
        uvs.extend([(0,0),(0,1),(1,1),(1,0)])
        colors.extend([color.rgba(shade,shade,shade,1)]*4)
        normals.extend([normal]*4)
    def ring(half,y):
        return [(-half,y,-half),(-half,y,half),(half,y,half),(half,y,-half)]
    inner, outer, bottom = ring(.455,.1), ring(.5,.035), ring(.5,-.14)
    quad(inner,1)
    for i in range(4):
        j = (i+1)%4
        quad([inner[i],outer[i],outer[j],inner[j]],.85)
        quad([outer[i],bottom[i],bottom[j],outer[j]],.57)
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, colors=colors, normals=normals)


class ClassicTheme:
    def __init__(self):
        Text.default_font = 'VeraMono.ttf'
        self.textures = {name:Texture(ASSETS/f'{name}.png')
                         for name in ['ember_background','limestone','fragile_stone',
                                      'oxidized_metal','soft_shadow']}
        # Nearest-neighbor sampling makes the fine metal grain crawl as it turns.
        # Ursina's mipmap setter only sets minification; set magnification too.
        self.textures['oxidized_metal'].filtering = 'bilinear'
        self.textures['oxidized_metal'].filtering = 'mipmap'
        self.slab = slab_mesh()
        self.background = Entity(parent=camera, model='quad', z=180, scale=(300,200),
                                 texture=self.textures['ember_background'], shader=unlit_shader,
                                 color=color.white, double_sided=True)

    def fit_background(self):
        fov = camera.lens.get_fov()
        self.background.scale = (360*tan(radians(fov.x)/2)*1.03,
                                 360*tan(radians(fov.y)/2)*1.03, 1)

    def tile(self, board, r, c):
        tile = board.getTile(r,c)
        if tile == Tile.GOAL:
            root = Entity(position=(c,-.1,-r), name='goal_hole')
            for x,z,w,d in [(-.47,0,.06,1),( .47,0,.06,1),(0,-.47,.88,.06),(0,.47,.88,.06)]:
                Entity(parent=root,model='cube',position=(x,-.13,z),scale=(w,.45,d),
                       texture=self.textures['limestone'],color=color.hex('#786c53'),shader=lit_with_shadows_shader)
                Entity(name='goal_rim',parent=root,model='cube',position=(x,.105,z),scale=(w,.025,d),
                       color=color.hex('#b89b60'),shader=lit_with_shadows_shader)
            Entity(name='goal_bottom',parent=root,model='cube',position=(0,-.4,0),scale=(.9,.04,.9),color=color.hex('#100d09'))
            return root
        shade = .94 + ((r*17+c*7)%11)*.008
        texture = self.textures['fragile_stone' if tile == Tile.FRAGILE else 'limestone']
        root = Entity(model=deepcopy(self.slab),position=(c,-.1,-r),scale=(.96,1,.96),
                      texture=texture,color=color.rgba(shade,shade,shade,1),shader=lit_with_shadows_shader,
                      double_sided=True)
        if tile == Tile.BRIDGE:
            root.color = color.hex('#91856d')
        if tile == Tile.SOFT_SWITCH:
            Entity(parent=root,model='circle',rotation_x=90,y=.112,scale=.55,
                   color=color.hex('#514a3e'),texture=self.textures['oxidized_metal'],shader=lit_with_shadows_shader)
            Entity(parent=root,model='circle',rotation_x=90,y=.118,scale=.36,
                   color=color.hex('#b7a686'),shader=lit_with_shadows_shader)
        elif tile == Tile.HEAVY_SWITCH:
            for angle in (-45,45):
                Entity(parent=root,model='cube',position=(0,.14,0),scale=(.66,.055,.14),
                       rotation_y=angle,color=color.hex('#655748'),texture=self.textures['oxidized_metal'],
                       shader=lit_with_shadows_shader)
        elif tile == Tile.SPLIT_SWITCH:
            for x in (-.18,.18):
                Entity(parent=root,model='cube',position=(x,.125,0),scale=(.22,.06,.50),
                       color=color.hex('#826699'),shader=lit_with_shadows_shader)
        if (r,c) in board.fatalCloseSwitches | board.fatalSplitSwitches:
            Text(parent=root,text='!',origin=(0,0),rotation=(90,0,0),y=.19,
                 scale=2,color=color.hex('#e53e22'))
        return root

    def shadow(self,r,c):
        return Entity(model='quad',rotation_x=90,position=(c+.16,-.75,-r-.12),
                      scale=(1.7,1.7),texture=self.textures['soft_shadow'],
                      shader=unlit_shader,color=color.white, double_sided=True)

    def block(self):
        root = Entity(model='cube',texture=self.textures['oxidized_metal'],
                      color=color.white,shader=lit_with_shadows_shader,origin_y=-.5)
        for x in (-.5,.5):
            for z in (-.5,.5):
                Entity(parent=root,model='cube',position=(x,.5,z),scale=(.022,1,.022),
                       color=color.hex('#503829'),shader=lit_with_shadows_shader)
        for y in (0,1):
            for x in (-.5,.5):
                Entity(parent=root,model='cube',position=(x,y,0),scale=(.022,.022,1),
                       color=color.hex('#503829'),shader=lit_with_shadows_shader)
            for z in (-.5,.5):
                Entity(parent=root,model='cube',position=(0,y,z),scale=(1,.022,.022),
                       color=color.hex('#503829'),shader=lit_with_shadows_shader)
        root._visual_parts = (root.model, *root.children)
        root._visual_rest = tuple(part.get_transform() for part in root._visual_parts)
        return root
