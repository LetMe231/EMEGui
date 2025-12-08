from PIL import Image, ImageDraw, ImageTk

def draw_smooth_arc(canvas, cx, cy, radius, start, extent, width=1, color="black"):
    size = radius * 2 + width * 2
    scale = 32


    big_size = size * scale
    big_img = Image.new("RGBA", (big_size, big_size), (255, 255, 255, 0))
    big_draw = ImageDraw.Draw(big_img)

    bbox = (width*scale, width*scale, big_size-width*scale, big_size-width*scale)

    # Pillow angles = clockwise, so invert
    big_draw.arc(bbox, start=start, end=(start+extent), fill=color, width=width*scale)

    # Downsample aggressively for smooth anti-aliasing
    img = big_img.resize((size, size), Image.LANCZOS)

    tk_img = ImageTk.PhotoImage(img)
    item_id = canvas.create_image(cx-radius-width, cy-radius-width, image=tk_img, anchor="nw")

    if not hasattr(canvas, "_images"):
        canvas._images = []
    canvas._images.append(tk_img)

    return item_id

def draw_smooth_line(canvas, x1, y1, x2, y2, width=1, color="black"):
    # Bounding box for the image that fully contains the line
    min_x, min_y = min(x1, x2), min(y1, y2)
    max_x, max_y = max(x1, x2), max(y1, y2)
    w, h = (max_x - min_x) + width*2, (max_y - min_y) + width*2

    scale = 12  # supersampling factor
    big_w, big_h = int(w * scale), int(h * scale)

    big_img = Image.new("RGBA", (big_w, big_h), (255, 255, 255, 0))
    big_draw = ImageDraw.Draw(big_img)

    # Coordinates scaled up
    sx1, sy1 = (x1 - min_x + width) * scale, (y1 - min_y + width) * scale
    sx2, sy2 = (x2 - min_x + width) * scale, (y2 - min_y + width) * scale

    big_draw.line((sx1, sy1, sx2, sy2), fill=color, width=width*scale)

    # Downsample to final size
    img = big_img.resize((int(w), int(h)), Image.LANCZOS)

    tk_img = ImageTk.PhotoImage(img)
    item_id = canvas.create_image(min_x - width, min_y - width, image=tk_img, anchor="nw")

    # Prevent garbage collection
    if not hasattr(canvas, "_images"):
        canvas._images = []
    canvas._images.append(tk_img)

    return item_id