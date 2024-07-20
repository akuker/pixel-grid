#!/usr/bin/env python3
#
# Based upon:
#   NeoPixel library strandtest example
#   Author: Tony DiCola (tony@tonydicola.com)
#
# Convert image using: https://ezgif.com/resize/ to match the resolution of your panel

import time

from PIL import Image
import os
import webcolors

try:
    from rpi_ws281x import *
except:
    print('Unable to load rpi_ws281x')

import argparse

# LED strip configuration:
LED_COUNT      = 900     # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating a signal (try 10)
LED_BRIGHTNESS = 40      # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


class simple_calc:
	LED_COLS_PER_PANEL = 10
	LED_ROWS_PER_PANEL = 10
	PANEL_COLS_PER_FRAME = 3
	PANEL_ROWS_PER_FRAME = 3
	LED_COLS_PER_FRAME = LED_COLS_PER_PANEL * PANEL_COLS_PER_FRAME
	LED_ROWS_PER_FRAME = LED_ROWS_PER_PANEL * PANEL_ROWS_PER_FRAME
	LEDS_PER_PANEL = LED_COLS_PER_PANEL * LED_ROWS_PER_PANEL
	PANELS_PER_FRAME = PANEL_COLS_PER_FRAME * PANEL_ROWS_PER_FRAME
	LEDS_PER_FRAME = PANELS_PER_FRAME * LEDS_PER_PANEL

	@staticmethod
	def calculate(cls, x, y):
		panel = (x // cls.LED_COLS_PER_PANEL) + (y // cls.LED_ROWS_PER_PANEL) * cls.PANEL_COLS_PER_FRAME
		# print(f"panel={panel}")
		return panel * cls.LEDS_PER_PANEL + (x % cls.LED_COLS_PER_PANEL) + (y % cls.LED_ROWS_PER_PANEL) * cls.LED_COLS_PER_PANEL


class GifFrameManager:
    def __init__(self):
        self.cur_image_file = None
        self.cur_image_file_name = ''
        self.cur_file_idx = 0
        self.cur_frame_idx = 0
        self.dir_path = './images'
        self.file_list = os.listdir(self.dir_path)

    def _open_next_file(self):
        self.file_list = os.listdir(self.dir_path)
        if(self.cur_file_idx > len(self.file_list)):
            self.cur_file_idx = 0
        file_name = self.file_list[self.cur_file_idx]
        self.cur_image_file_name = os.path.join(self.dir_path, file_name)
        print(f'Opening {self.cur_image_file_name}')
        new_file_handle = Image.open(self.cur_image_file_name)
        self.cur_frame_idx = 0 
        # Increment to next file
        self.cur_file_idx = (self.cur_file_idx + 1) % len(self.file_list)
        return new_file_handle

    def _get_next_frame(self):
        self.cur_image_file.seek(self.cur_frame_idx)
        frame_data = list(self.cur_image_file.getdata())
        frame_pixels = [frame_data[i:i+self.cur_image_file.size[0]] for i in range(0, len(frame_data), self.cur_image_file.size[0])]
        # print(f'size of pixels {len(frame_pixels)} {len(frame_pixels[0])}')
        
        self.cur_frame_idx = self.cur_frame_idx + 1
        # Check if we went beyond the end of the image
        if(self.cur_frame_idx >= self.cur_image_file.n_frames):
            # print(f'Frame {self.cur_frame_idx} is beyond the end of the image {self.cur_image_file_name}')
            self.cur_image_file = None
            self.cur_image_file_name = ''
        return frame_pixels

    def next_frame(self):
        if(self.cur_image_file is None):
            self.cur_image_file = self._open_next_file()
        return self._get_next_frame()
        
class DummyStrip():
    def __init__(self):
        pass
    def show(self):
        pass
    def setPixelColor(self, idx, color):
        pass
        


def set_dimmer(c) -> int:
	# print(f'set_dimmer({c})')
	r = int(((c >> 8) & 0xFF) * LED_BRIGHTNESS/255)
	g = int(((c >> 16) & 0xFF) * LED_BRIGHTNESS/255)
	b = int((c & 0xFF) * LED_BRIGHTNESS/255)
	return (g<<16) + (r<<8) + b
	

def draw_frame(strip, frame_pixels):
    cur_pixel_idx = 0

    start = time.time()
    for row in frame_pixels:
        for color in row:
            if type(color) == int: continue
            
            my_x = cur_pixel_idx % simple_calc.LED_COLS_PER_FRAME
            my_y = cur_pixel_idx // simple_calc.LED_COLS_PER_FRAME
            led_buff_idx = simple_calc.calculate(cls=simple_calc, x=my_x, y=my_y)
            wscolor = Color(color[0], color[1], color[2])
            wscolor_dimmer = set_dimmer(Color(color[0], color[1], color[2]))
            strip.setPixelColor(led_buff_idx, wscolor_dimmer)
            cur_pixel_idx = cur_pixel_idx+1
    finish = time.time()
    # print(f'processing time: {finish - start}')
    strip.show()

def get_gif_frames(gif_path, output_dir):
    frames = []
    unknown_count = 1
    all_pixels_data = os.path.join(output_dir, f"frame_all.py")
    with open(all_pixels_data, 'w') as all_pix_data:
        all_pix_data.write(f'pixel_data = [\n')
        with Image.open(gif_path) as im:
            for frame_index in range(im.n_frames):
                im.seek(frame_index)
                frame_data = list(im.getdata())
                frame_pixels = [frame_data[i:i+im.size[0]] for i in range(0, len(frame_data), im.size[0])]
                print(f'size of pixels {len(frame_pixels)} {len(frame_pixels[0])}')
                frames.append(frame_pixels)

                # Make sure that all colors are stored in the dictionary
                for row in frame_pixels:
                    for color in row:
                        if type(color) == int: continue
                        color = closest_color_tuple(color)
                        # color = simplify_color(color)
                        if color not in colors_dict:
                            # simplified_color = simplify_color(color)
                            color_name = get_color_name(color)
                            # print(f'original: {webcolors.rgb_to_hex(color)} new: {webcolors.rgb_to_hex(simplified_color)}')
                            
                            color_rgb = webcolors.name_to_rgb(color_name)
                            color_rgb_tuple = (color_rgb.red, color_rgb.green, color_rgb.blue)
                            print(f'new color {color} = {color_name} - {color_rgb_tuple}')
                            colors_dict[color_rgb_tuple] = color_name


                            # colors_dict[color] = len(colors_dict) + 1

                pixel_data_path = os.path.join(output_dir, f"frame_{frame_index}.py")
                with open(pixel_data_path, 'w') as f:
                    f.write(f'frame_{frame_index}_data = (\n')
                    all_pix_data.write(f'\t[')
                    # Parse the pixels, then generate an array of pixels with a count
                    cur_pixel = ''
                    cur_count = 0
                    for row in frame_pixels:
                        for pixel in row:
                            if pixel == cur_pixel:
                                cur_count += 1
                                continue
                            if cur_pixel:
                                pixel_name = colors_dict.get(cur_pixel, f'UNKNOWN_{unknown_count}')
                                if pixel_name.startswith('UNKNOWN'):
                                    unknown_count += 1
                                    colors_dict[cur_pixel] = pixel_name
                                # print(f'{pixel_name} {cur_count}')
                                f.write(f'\t({pixel_name}, {cur_count}),\n')
                                all_pix_data.write(f'({pixel_name}, {cur_count}), ')
                                
                            cur_pixel = pixel
                            cur_count = 1
                    f.write(')')
                    all_pix_data.write('],\n')

                # Save the current frame as a separate file
                frame_path = os.path.join(output_dir, f"frame_{frame_index}.png")
                im.save(frame_path)
                csv_path = os.path.join(output_dir, f"frame_{frame_index}.csv")
                with open(csv_path, 'w') as f:
                    for row in frame_pixels:
                        f.write(','.join(map(str, row)) + '\n')
        all_pix_data.write(']\n')
    print(f'colors dict: {colors_dict}')
    return frames



# # Create the output directory if it doesn't exist
# os.makedirs(output_dir, exist_ok=True)

# frames = get_gif_frames(gif_path, output_dir)

# for i, frame in enumerate(frames):
#     print(f"Frame {i} saved to file.")




# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=0):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)

def theaterChase(strip, color, wait_ms=0, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, wheel((i+j) % 255))
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# Main program logic follows:
if __name__ == '__main__':
    # Process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()

    try:
        # Create NeoPixel object with appropriate configuration.
        strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        # Intialize the library (must be called once before other functions).
        strip.begin()
    except:
        print('running without neopixels')
        strip = DummyStrip()

    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')

    try:

        frame_mgr = GifFrameManager()
        while True:

            current_image = frame_mgr.next_frame()
            draw_frame(strip, current_image)

    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)

