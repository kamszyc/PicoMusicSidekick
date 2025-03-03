import usb_hid
import usb_cdc
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
import time
import board
from digitalio import DigitalInOut, Direction, Pull
import asyncio
import keypad
import busio
import terminalio
import displayio
import json
from fourwire import FourWire
from adafruit_display_text import label, scrolling_label
import adafruit_ili9341
from xpt2046 import Touch
from adafruit_button import Button

TFT_WIDTH = 320
TFT_HEIGHT = 240

touch_spi_clk = board.GP10
touch_spi_mosi = board.GP11
touch_spi_miso = board.GP8

touch_cs = board.GP12

touch_x_min = 120
touch_x_max = 1847
touch_y_min = 148
touch_y_max = 1914

touch_spi = busio.SPI(touch_spi_clk, MOSI=touch_spi_mosi, MISO=touch_spi_miso)
touch = Touch(touch_spi, cs=touch_cs,
            x_min=touch_x_min, x_max=touch_x_max,
            y_min=touch_y_min, y_max=touch_y_max)

taskInterval_50ms = 0.050
NxTick = time.monotonic() + taskInterval_50ms

EVT_NO = const(0)
EVT_PenDown = const(1)
EVT_PenUp   = const(2)
EVT_PenRept = const(3)
touchEvent  = EVT_NO

touchSt_Idle_0     = const(0)
touchSt_DnDeb_1    = const(1)
touchSt_Touching_2 = const(2)
touchSt_UpDeb_3    = const(3)
touchSt = touchSt_Idle_0

touchDb_NUM = const(3)
touchDb = touchDb_NUM
touching = False
    

async def handle_touch():
    global NxTick
    global touchEvent
    global touchedX, touchedY
    cc = ConsumerControl(usb_hid.devices)
    while True:
        curTick = time.monotonic()
        if curTick >= NxTick:
            NxTick = curTick + taskInterval_50ms
            #print(NxTick)
            touch_det_task()
            
        #handle touch event
        if touchEvent != EVT_NO:
            if touchEvent == EVT_PenDown:
                print('ev PenDown - ', touchedX, " : ", touchedY)

            if touchEvent == EVT_PenUp:
                print('ev PenUp - ')
                
                cc.send(ConsumerControlCode.PLAY_PAUSE)
                
            touchEvent = EVT_NO

        await asyncio.sleep(0)

def touch_det_task():
    global touch
    global touching
    global touchSt
    global touchEvent
    global touchedX, touchedY
    global touchDb
    
    validXY = valid_touch(TFT_HEIGHT, TFT_WIDTH)

    if touchSt == touchSt_Idle_0:
        if validXY != None:
            touchDb = touchDb_NUM
            touchSt = touchSt_DnDeb_1
    
    elif touchSt == touchSt_DnDeb_1:
        if validXY != None:
            touchDb = touchDb-1
            if touchDb==0:
                touchSt = touchSt_Touching_2
                touchEvent = EVT_PenDown
                touchedX, touchedY = validXY
                touching = True
        else:
            touchSt = touchSt_Idle_0
            
    elif touchSt == touchSt_Touching_2:
        if validXY != None:
            touchedX, touchedY = validXY
            touchEvent = EVT_PenRept
        else:
            touchDb=touchDb_NUM
            touchSt = touchSt_UpDeb_3
            
    elif touchSt == touchSt_UpDeb_3:
        if validXY != None:
            touchSt = touchSt_Touching_2
        else:
            touchDb=touchDb-1
            if touchDb==0:
                touchSt = touchSt_Idle_0
                touchEvent = EVT_PenUp
                touching = False


def valid_touch(scrWidth, scrHeight):
    xy = touch.raw_touch()
    
    if xy == None:
        return None
    
    normailzedX, normailzedY = touch.normalize(*xy)
    if (normailzedX < 0 or normailzedX >= scrWidth
            or normailzedY < 0 or normailzedY >= scrHeight):
            return None
        
    return (normailzedX, normailzedY)


async def render_display():
    displayio.release_displays()

    tft_spi_clk = board.GP6
    tft_spi_mosi = board.GP7
    tft_cs = board.GP13
    tft_dc = board.GP15
    tft_res = board.GP14

    tft_spi = busio.SPI(tft_spi_clk, MOSI=tft_spi_mosi)

    display_bus = displayio.FourWire(
        tft_spi, command=tft_dc, chip_select=tft_cs, reset=tft_res)

    display = adafruit_ili9341.ILI9341(display_bus,
                        width=TFT_WIDTH, height=TFT_HEIGHT)
    display.rotation = 90
    scrWidth = display.width
    scrHeight = display.height

    splash = displayio.Group()
    display.root_group = splash

    text_group = displayio.Group(scale=2, x=10, y=10)
    artist_label = scrolling_label.ScrollingLabel(terminalio.FONT, text="Waiting...", max_characters = 20, animate_time=0.5)
    text_group.append(artist_label) 
    title_label = scrolling_label.ScrollingLabel(terminalio.FONT, text="Play some music!", max_characters = 20, animate_time=0.5)
    title_label.y = 20
    text_group.append(title_label)
    splash.append(text_group)


    
    # --| Button Config |-------------------------------------------------
    BUTTON_X = 95
    BUTTON_Y = 95
    BUTTON_WIDTH = 50
    BUTTON_HEIGHT = 50
    BUTTON_STYLE = Button.RECT
    BUTTON_FILL_COLOR = 0x00FFFF
    BUTTON_OUTLINE_COLOR = 0xFF00FF
    BUTTON_LABEL = "PLAY"
    BUTTON_LABEL_COLOR = 0x000000

    # --| Button Config |-------------------------------------------------

    # Make the button
    button = Button(
        x=BUTTON_X,
        y=BUTTON_Y,
        width=BUTTON_WIDTH,
        height=BUTTON_HEIGHT,
        style=BUTTON_STYLE,
        fill_color=BUTTON_FILL_COLOR,
        outline_color=BUTTON_OUTLINE_COLOR,
        label=BUTTON_LABEL,
        label_font=terminalio.FONT,
        label_color=BUTTON_LABEL_COLOR,
    )
    splash.append(button)

    while True:
        if usb_cdc.data.in_waiting > 0:
            try:
                data_in = usb_cdc.data.readline()
                if data_in:
                    try:
                        request = json.loads(data_in)
                        if artist_label.text.strip() != request["artist"]:
                            artist_label.text = request["artist"]
                        if title_label.text.strip() != request["title"]:
                            title_label.text = request["title"]
                    except ValueError:
                        pass
            except Exception as e:
                print("error")

        artist_label.update()
        title_label.update()

        display.refresh()

        await asyncio.sleep(0.1)

async def main():
    handle_touch_task = asyncio.create_task(handle_touch())
    render_display_task = asyncio.create_task(render_display())
    await asyncio.gather(handle_touch_task, render_display_task)

asyncio.run(main())