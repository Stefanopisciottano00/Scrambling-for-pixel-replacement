# Questo script permette di creare un video scramblato sulla ROI del volto, funziona solo per un soggetto alla volta.

import time
from blind_watermark import WaterMark
import mediapipe as mp
import cv2
import numpy as np
import skvideo.io
from PIL import Image
from stegano import lsb


mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()
import random



#==================================         FUNCTION FOR DETECTING FACIAL LANDMARKS         =====================================#

def get_facial_landmarks(frame):
    height, width, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(frame_rgb)

    facelandmarks = []
    for facial_landmarks in result.multi_face_landmarks:
        for i in range(0, 468):
            pt1 = facial_landmarks.landmark[i]
            x = int(pt1.x * width)
            y = int(pt1.y * height)
            facelandmarks.append([x, y])
    return np.array(facelandmarks, np.int32)

#==================================         FUNCTION FOR DIVIDING IMAGE INTO BLOCKS        =====================================#


def scramble_frame(img, splits):
    height, width, _ = img.shape
    dimensione_blocco_x = width // splits
    dimensione_blocco_y = height // splits
    blocchi = []

    if height % splits != 0 or width % splits != 0:
        raise ValueError("Le dimensioni dell'immagine non sono divisibili in modo uniforme per il numero di suddivisioni desiderate.")
    if height % dimensione_blocco_y != 0 or width % dimensione_blocco_x != 0:
        raise ValueError("Le dimensioni della regione ritagliata non sono compatibili con le dimensioni delle sottosezioni di blocco.")

    for y in range(splits):
        for x in range(splits):
            inizio_x = x * dimensione_blocco_x
            inizio_y = y * dimensione_blocco_y
            fine_x = (x + 1) * dimensione_blocco_x
            fine_y = (y + 1) * dimensione_blocco_y
            blocco = img[inizio_y:fine_y, inizio_x:fine_x]
            blocchi.append(blocco)
    
    # blocchi_casuali = blocchi
    # random.shuffle(blocchi_casuali)
    dizionario_blocchi = {}
    for i, blocco in enumerate(blocchi):
        dizionario_blocchi[i] = blocchi[i]

    # Mescolare le chiavi
    chiavi_mescolate = list(dizionario_blocchi.keys())
    random.shuffle(chiavi_mescolate)

    nuovo_dizionario = {}
    for chiave in chiavi_mescolate:
        nuovo_dizionario[chiave] = dizionario_blocchi[chiave]

    # Creazione dell'immagine scramblata
    larghezza_blocco, altezza_blocco, _ = list(nuovo_dizionario.values())[0].shape
    larghezza_unione = larghezza_blocco * splits
    altezza_unione = altezza_blocco * splits

    immagine_unione = np.zeros((altezza_unione, larghezza_unione, 3), dtype=np.uint8)

    for y in range(splits):
        for x in range(splits):
            indice = y * splits + x
            chiave = list(nuovo_dizionario.keys())[indice]
            blocco_casuale = nuovo_dizionario[chiave]
            inizio_y = y * altezza_blocco
            fine_y = (y + 1) * altezza_blocco
            inizio_x = x * larghezza_blocco
            fine_x = (x + 1) * larghezza_blocco
            immagine_unione[inizio_y:fine_y, inizio_x:fine_x] = blocco_casuale

    #Adesso immagine unione contiene l'immagine scramblata mentre il 
    #dizionario nuovo_dizionario contiene come sono scambiate le immagini

    return immagine_unione, list(nuovo_dizionario.keys())
#==================================         FUNCTION FOR SCRAMBLING EVERY SINGLE FRAME         =====================================#

def scrambleface(img, splits):

    key_frame=[]

    if isinstance(img, str):
        img = cv2.imread(img)
        if img is None:
            raise ValueError("Could not read the image")

    h, w, _ = img.shape
    landmarks = get_facial_landmarks(img)
    hull = cv2.convexHull(landmarks)

    x, y, w, h = cv2.boundingRect(hull)
    max_side = 240

    if (w or h) > 240:
        max_side = 480

    x_centered = x + (w - max_side) // 2
    y_centered = y + (h - max_side) // 2

    # Informazioni sulla posizione del rettangolo del volto, che faranno parte della chiave
    info_rettangolo = [x_centered, y_centered, max_side]

    roi = img[y_centered:y_centered + max_side, x_centered:x_centered + max_side]

    # Informazioni sulla posizione dei pixel nell'immagine scramblata, che faranno parte della chiave
    img_scrambled, info_scramble = scramble_frame(roi, splits)

    img[y_centered:y_centered + max_side, x_centered:x_centered + max_side] = img_scrambled

    key_frame = [info_rettangolo, info_scramble]

    return img, key_frame

   

#==================================       FUNCTION FOR SCRAMBLING LOOP FOR VIDEOS        =====================================#

def scramblevideo(input_video_path, output_video_path, splits):
   
    if splits is None:
        raise ValueError("Please insert a value for splitting the image!")

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {input_video_path}.")
        return
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    codec = cv2.VideoWriter_fourcc(*'RAW ')

    writer = skvideo.io.FFmpegWriter(output_video_path, outputdict={
    '-vcodec': 'libx264',  #use the h.264 codec
    '-crf': '0',           #set the constant rate factor to 0, which is lossless
    '-preset':'veryslow'   #the slower the better compression, in princple, try 
                           #other options see https://trac.ffmpeg.org/wiki/Encode/H.264
    }) 
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if output_video_path:
        out = cv2.VideoWriter(output_video_path, codec, fps, (frame_width, frame_height))
    else:
        out = None
        print("No output path specified. The scrambled video won't be saved.")

    frame_number = 0
    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            print("Reached the end of the video.")
            break

        try:
            img, first_key = scrambleface(frame, splits)

            data_str = str(first_key)
            cv2.imwrite("temp/img.jpg", img)

            #---------------------------------------------------------------------------------------------------------------------------------
            # Inserimento del watermark all'interno dell'immagine, per una regione di 64 pixel la lunghezza del watermark sarà di:      2119
            #---------------------------------------------------------------------------------------------------------------------------------

            bwm1 = WaterMark(password_img=1, password_wm=1)
            bwm1.read_img('temp/img.jpg')
            bwm1.read_wm(data_str, mode='str')
            img_watermarked = bwm1.embed('temp/persona.jpg', compression_ratio=80)

            # out.write(img_watermarked)
            writer.writeFrame(img_watermarked[:,:,::-1])  #write the frame as RGB not BGR

        except Exception as e:
            print(f"Error in the frame {frame_number}: {str(e)}")
            scrambled_frame = frame

        print(f"Frame {frame_number}/{total_frames}")
        frame_number += 1

    writer.close()
    cap.release()
    if out:
        out.release()

    cv2.destroyAllWindows()
    print("Video processing completed.")



#==================================         MAIN PROGRAM         =====================================#


from blind_watermark import WaterMark
import cv2

scramble_settings = {
    'splits': 5,
    'type': 'pixel',
    'bg': True,
    'seamless': False,
    'scramble_ratio': 0.1,
    'seed': 1,
    'write': False 
}

mpeg_video = 'testSet/safari.mpeg'
video_path = 'testSet/hi.mp4'
long_video_path = 'testSet/Human_safari.mp4'

#Inserire 8 come ultimo parametro, questo permetterà di avere uno scrambling di 64 regioni ed ottenere un risultato migliore
scramblevideo(video_path, "scrambled_videos/hi.mp4", 8)