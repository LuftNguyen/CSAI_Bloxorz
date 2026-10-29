"""Generate original short mono PCM sound effects, using only the stdlib."""
from pathlib import Path
import math
import random
import struct
import wave

ROOT = Path(__file__).resolve().parents[1] / 'assets/classic/audio'
RATE = 22050
SPECS = {
    'stone': (.18, 115, .65, 24),
    'bridge': (.28, 210, .35, 16),
    'fragile': (.22, 390, .75, 22),
    'break': (.40, 620, .90, 12),
    'switch': (.14, 740, .15, 27),
    'split': (.38, 470, .08, 7),
    'merge': (.26, 230, .20, 15),
    'select': (.09, 980, .03, 35),
    'fall': (.55, 340, .25, 6),
    'win': (.65, 523, .02, 4),
    'trap': (.48, 160, .16, 8),
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for index, (name, (duration, frequency, noise, decay)) in enumerate(SPECS.items()):
        rng = random.Random(870 + index)
        phase = 0
        samples = []
        smooth = 0
        for i in range(int(duration * RATE)):
            t = i / RATE
            pitch = frequency
            if name == 'fall':
                pitch *= max(.12, 1-t/duration)
            elif name == 'split':
                pitch *= 1+t*2
            elif name == 'win':
                pitch *= (1, 1.25, 1.5)[min(2, int(t/.18))]
            phase += 2*math.pi*pitch/RATE
            smooth = .55*smooth + .45*rng.uniform(-1,1)
            tone = math.sin(phase)*.7 + math.sin(phase*2.37)*.3
            envelope = min(1, t/.005)*math.exp(-decay*t)
            envelope *= min(1, (duration-t)/.025)
            value = .65*envelope*((1-noise)*tone + noise*smooth)
            samples.append(int(max(-1,min(1,value))*32767))
        with wave.open(str(ROOT/f'{name}.wav'), 'wb') as output:
            output.setparams((1,2,RATE,0,'NONE','not compressed'))
            output.writeframes(struct.pack(f'<{len(samples)}h',*samples))
    print(f'Generated {len(SPECS)} original sound effects in {ROOT}')


if __name__ == '__main__':
    main()
