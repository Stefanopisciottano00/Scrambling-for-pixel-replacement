# In questo script viene estratto il watermark presente all'interno di un video scramblato e viene ripristinato il video originale
# a partire da una ROI di 64 pixel, e un watermark di 2119 bit

import re
import time
import cv2
import numpy as np
from stegano import lsb
from blind_watermark import WaterMark

def extract_numbers_from_string(input_string):
    numbers = re.findall(r'\d+', input_string)

    numbers = [int(number) for number in numbers]
    return numbers

codec = cv2.VideoWriter_fourcc('M','P','G','1')
fps = 30

video_path = 'scrambled_videos/hi.mp4'
output_video_path = "descrambled_videos/video_finale.mp4"

cap = cv2.VideoCapture(video_path)
len_wm = 2119
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if output_video_path:
    out = cv2.VideoWriter(output_video_path, codec, fps, (frame_width, frame_height))

if not cap.isOpened():
    print("Errore nell'apertura del video.")
    exit()

line_index = 0
frame_count = 0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

while cap.isOpened():
    ret, frame = cap.read()

    print(f"processing frame {frame_count}/{total_frames}")
    frame_count += 1

    if not ret:
        break

    cv2.imwrite("temp/img_watermarked.jpg", frame)

    bwm1 = WaterMark(password_img=1, password_wm=1)
    wm_extract = bwm1.extract('temp/img_watermarked.jpg', wm_shape=len_wm, mode='str')  #Contiene il watermark correttamente estratto


    scrambling_positions = wm_extract.split("], [")[1]
    scrambling_numbers = extract_numbers_from_string(scrambling_positions)


    rectangle_positions = wm_extract.split("], [")[0]
    rectangle_numbers = extract_numbers_from_string(rectangle_positions)

    
    xr = rectangle_numbers[0]
    yr = rectangle_numbers[1]
    side = rectangle_numbers[2]

    if ( len(scrambling_numbers) == 64):
        splits = 8
        middle_x = side // 8
        middle_y = side // 8

    face_region = frame[yr:yr+side, xr:xr+side]

    dimensione_blocco_x = side // splits
    dimensione_blocco_y = side // splits
    blocchi = []

    for y in range(splits):
        for x in range(splits):
            inizio_x = x * dimensione_blocco_x
            inizio_y = y * dimensione_blocco_y
            fine_x = (x + 1) * dimensione_blocco_x
            fine_y = (y + 1) * dimensione_blocco_y
            blocco = face_region[inizio_y:fine_y, inizio_x:fine_x]
            blocchi.append(blocco)

    for i, element in enumerate(scrambling_numbers):
        globals()[f"var{i+1}"] = element
    

    # Creazione del dizionario per il matching tra le parti dell'immagine, e l'array dello scrambling.
    # Per maggiori informazioni vedere la cartella esempi
    dictionary = {}

    for i in range(1, 65):
        dictionary[str(eval(f"var{i}"))] = blocchi[i - 1]

    scrambled_img = np.zeros_like(face_region)

    for i in range(8):
        for j in range(8):
            start_row = i * (side//8)
            end_row = (i + 1) * (side//8)
            start_col = j * (side//8)
            end_col = (j + 1) * (side//8)
            
            region_key = str(i * 8 + j)  # Calcola la chiave del dizionario
            scrambled_img[start_row:end_row, start_col:end_col] = dictionary.get(region_key)

    frame[yr:yr+side, xr:xr+side] = scrambled_img

    if out:
      out.write(frame)

    line_index += 1

cap.release()
cv2.destroyAllWindows()