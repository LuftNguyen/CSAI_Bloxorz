"""Original deterministic textures for the classic renderer; no external artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math
import random

ROOT = Path(__file__).resolve().parents[1] / 'assets/classic'


def noise(size, coarse, seed):
    rng = random.Random(seed)
    im = Image.new('L', coarse)
    im.putdata([rng.randrange(256) for _ in range(coarse[0]*coarse[1])])
    return im.resize(size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2))


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    w, h = 1024, 640
    clouds = noise((w,h), (10,7), 41)
    grain = noise((w,h), (100,64), 42)
    bg = Image.new('RGB', (w,h))
    pixels = []
    for y in range(h):
        t = y/(h-1)
        for x in range(w):
            n = clouds.getpixel((x,y))/255
            g = grain.getpixel((x,y))/255-.5
            edge = ((x/w-.5)**2*1.25 + (t-.35)**2*.7)
            glow = max(0, 1-edge)*(.82+.22*n)
            smoke = max(0, t-.55)*(1-n)*150
            pixels.append(tuple(max(0,min(255,int(v))) for v in
                          ((202-117*t)*glow-smoke+g*5,
                           (49-34*t)*glow-smoke*.3+g*3,
                           (12-7*t)*glow+g*2)))
    bg.putdata(pixels)
    bg.save(ROOT/'ember_background.png')
    rng = random.Random(73)
    stone = Image.new('RGB',(128,128))
    field = noise(stone.size,(14,14),74)
    stone.putdata([(v-5,v,v-2) for y in range(128) for x in range(128)
                   for v in [max(130,min(215,int(179+field.getpixel((x,y))*.12+rng.gauss(0,5))))]])
    draw = ImageDraw.Draw(stone)
    for _ in range(48):
        x,y = rng.randrange(128),rng.randrange(128)
        draw.line((x,y,x+rng.randrange(2,12),y+rng.randrange(-2,3)),fill=(165,170,166),width=1)
    stone.save(ROOT/'limestone.png')
    fragile = stone.copy()
    tint = Image.new('RGB',stone.size,(211,134,38))
    fragile = Image.blend(fragile,tint,.78)
    draw = ImageDraw.Draw(fragile)
    for path in [[(0,35),(29,43),(46,69),(80,72),(110,106)],
                 [(46,69),(37,98),(44,128)],[(80,72),(95,41),(128,32)]]:
        draw.line(path,fill=(97,72,49),width=1)
    fragile.save(ROOT/'fragile_stone.png')
    coarse = noise((256,256),(13,13),90)
    rust = Image.new('RGB',(256,256))
    rust.putdata([tuple(max(0,min(255,int(v))) for v in
                        (43+104*n+g,44+45*n+g,42+18*n+g))
                  for y in range(256) for x in range(256)
                  for n in [(coarse.getpixel((x,y))/255)**1.5]
                  for g in [rng.gauss(0,8)]])
    ImageDraw.Draw(rust).rectangle((0,0,255,255),outline=(72,51,36),width=3)
    rust.save(ROOT/'oxidized_metal.png')
    shadow = Image.new('RGBA',(128,128))
    shadow.putdata([(0,0,0,int(105*max(0,1-((x-63.5)/64)**2-((y-63.5)/64)**2)**2))
                    for y in range(128) for x in range(128)])
    shadow.save(ROOT/'soft_shadow.png')
    button = Image.new('RGB',(192,64))
    button.putdata([(int(181-43*y/64),int(119-42*y/64),int(62-26*y/64))
                    for y in range(64) for x in range(192)])
    d = ImageDraw.Draw(button)
    d.rectangle((0,0,191,63),outline=(58,25,9),width=3)
    d.line((3,3,188,3),fill=(239,180,107),width=2)
    d.line((188,5,188,60),fill=(78,35,12),width=2)
    button.save(ROOT/'bronze_button.png')
    print('Generated six classic textures:',ROOT)


if __name__ == '__main__':
    main()
