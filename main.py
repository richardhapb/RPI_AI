import os
import sys
import json
import vosk
import pyaudio
from openai import OpenAI
from gtts import gTTS
import time
import config
import icloud
import requests
import spotify
from spotipy import SpotifyException

client = OpenAI(api_key=config.OPENAI_APIKEY)

NAME_AI = "octavia"

# Keywords

kwrds_activation = [NAME_AI]
kwrds_greetings = ["buen día", "hola " + NAME_AI, "muy buenos días", "buenos días"]
kwrds_chatgpt_data = ['tengo una duda', 'ayúdame con algo', 'ayúdeme con algo', 'ayudarme con algo']
kwrds_chatgpt = ['inicia una conversación', 'hablémos por favor', 'inicia un chat', 'necesito respuestas', 'iniciar un chat', 'pon un chat']
kwrds_lamp_on = ['enciende la luz', 'prende la luz', 'luz por favor', 'enciende la luz por favor']
kwrds_lamp_off = ['apaga la luz', 'quita la luz', 'apaga la luz por favor']

MAX_TOKENS = 200
PLAYER = "cvlc --play-and-exit "

DEV = False
REQUEST = "buen día"
RATE = 16000
CHUNK = 1024  # Tamaño del fragmento de audio (puede ser 1024, 2048, 4000, etc.)

# Inicialización de PyAudio y apertura del flujo de entrada
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
stream.start_stream()

if not os.path.exists("model"):
    print("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.")
    sys.exit(1)
    
model = vosk.Model("model")
recognizer = vosk.KaldiRecognizer(model, RATE)

def recognize(data):
    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        return result
    else:
        return {}

def listen(max_listening_time=5):
    data = b""
    start_time = time.time()

    while time.time() - start_time < max_listening_time:
        try:
            chunk = stream.read(CHUNK, exception_on_overflow=False)
            data += chunk
        except Exception as e:
            print(f"Error al leer el audio: {e}")
            break
    result = recognize(data)
    if result and 'text' in result:
        res = result['text']
    else:
        res = "error"

    return res

def speak(text):
    playing_music = spotify.is_playing()
    if playing_music:
        spotify.pause()
    tts = gTTS(text, lang="es", tld="com.mx")
    tts.save("response.mp3")
    os.system(PLAYER + "response.mp3")

    if playing_music:
        spotify.resume()

def weather(kind='weather', fc_days=1):

    '''
    kind = weather, forecast
    '''

    ## lat y lon La Cisterna
    lat = -33.51738141625813
    lon = -70.6567828851336

    BASE_URL = "http://api.weatherapi.com/v1"
    PARAMS = f"?lang=es&key={config.WEATHER_API_KEY}&q={lat},{lon}"
    PARAMS += f"&days={fc_days}" if kind == 'forecast' else ""
    
    req = {
        "weather": "/current.json",
        "forecast": f"/forecast.json"
    }

    responses = {
        "weather": "current",
        "forecast": "forecast"
    }

    try:
        response = requests.get(BASE_URL + req[kind] + PARAMS).json()[responses[kind]]
        if kind == 'forecast':
            response = response['forecastday'][0]['day']
    except KeyError as e:
        print("La solicitud no fue exitosa")
        raise KeyError(e)
    except Exception as e:
        print("Error al obtener la información")
        print(e)
        response = "error"
        raise Exception(e)
    
    return response


def manage_request(request):
    response = ""
    if request in kwrds_greetings:
        response = greetings()
    elif request in kwrds_chatgpt:
        prompt = ""
        speak("Si Richard, dime que necesitas")
        while True:
            prompt = listen(10)
            print(listen)
            exit = ["gracias", "nada más", "estamos ok", "estamos listos", "con eso estamos"]
            if prompt in exit:
                speak("De nada Richard, avísame si necesitas algo más")
                break
            gpt = chatgpt(prompt)
            print(gpt)
            speak(gpt)

    elif request in kwrds_chatgpt_data:
        response = chatgpt_data()
    elif request in kwrds_lamp_on:
        response = lamp(True)
    elif request in kwrds_lamp_off:
        response = lamp(False)
    elif "música" in  request:
        try:
            if "detén" in request or "pausa" in request:
                spotify.pause()
            elif "reanuda" in request or "continúa" in request or "play" in request:
                spotify.resume()
            else:
                last_word = request.split(" ")[-1]
                if last_word == "música":
                    spotify.playlist()
                elif last_word == "viajar":
                    spotify.playlist("spotify:playlist:47RDqYFo357tW5sIk5cN8p")
                elif last_word == "estudiar":
                    spotify.playlist("spotify:playlist:1YIe34rcmLjCYpY9wJoM2p")
                elif last_word == "relajarme":
                    spotify.playlist("spotify:playlist:0qPA1tBtiCLVHCUfREECnO")
        except SpotifyException:
            speak("Hay un problema con Spotify")
        except ValueError as e:
            print(e)
            speak(str(e))
    elif request == "adiós " + NAME_AI:
        response = "exit"
    return response


# Funciones de acción

def greetings():
    speak("Hola Richard, muy buenos días, ¡espero estés excelente!")

    #### WEATHER
    try:
        w = weather()
        f = weather('forecast')

        if w['temp_c'] < 16:
            speak("Hoy hace frío")
        elif w['temp_c'] < 20:
            speak("Está un poco frío, pero no mucho para ti")
        else:
            speak("Hoy hace calor")

        speak(f"El cielo está {w['condition']['text']}")    
        
        speak(f"La temperatura actual es {w['temp_c']} grados celcius")
        speak(f"Se espera una mínima de {f['mintemp_c']} y una máxima de {f['maxtemp_c']} grados celcius")
        speak(f"La probabilidad de lluvia es {f['daily_chance_of_rain'] * 100}%")
    except KeyError:
        print("Error al obtener el clima")
    except Exception as e:
        print("Hubo en error")
        print(e)

    try:
        # reminders = icloud.reminders_today()
        events = icloud.calendar_today()
        events = []

        if events:
            speak("Estos son tus eventos para hoy: ")
            for e in events:
                speak(e)
        else:
            speak("No tienes eventos agendados para hoy")
    except ConnectionError:
        print("Hubo un error al obtener los datos de iCloud")

    ### Frase motivadora
    try:
        prompt = "Dame una frase motivadora potente, que haya dicho una persona exitósa, filósofo o científico. Que sea inspiradora. Damelo en texto plano, no uses markdown."

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=MAX_TOKENS
        )
        res = response.choices[0].message.content
        speak("Tengo una frase motivadora para ti")
        print(res)
        speak(res)
    except Exception as e:
        print("Hubo un error al obtener la frase motivadora")

    return "¡Que tengas un excelente día!"

def chatgpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres una asistente de mi centro de trabajo y hogar, me ayudas en mi planificación diaria y en llevar a cabo mis proyectos, tu nombre es Octavia, mi nombre es Richard. Responde en texto plano, sin usar Markdown durante toda la conversación."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7
    )

    res = response.choices[0].message.content
    print(res)
    return res

def chatgpt_data():
    prompt = ""

    speak("¿En qué te puedo ayudar?")

    # Escuchar por 10 segundos
    prompt = listen(10)

    if DEV:
        prompt = "Dame una frase motivadora potente"

    print(f"prompt: {prompt}")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=MAX_TOKENS,
        format="text"
    )
    res = response.choices[0].message.content
    print(res)
    return res

def lamp(on=True):
    res = ""
    if on:
        res = "Lámpara encendida"
    else:
        res = "Lámpara apagada"
    return res
        

def main():
    response = ""
    try:
        while True:
            print("Escuchando...")
            while True:
                if DEV:
                    response = manage_request(REQUEST)
                    break
                else:
                    request = listen(5)
                    print(request)
                    response = manage_request(request)
                    if response == "error" or request == "error":
                        speak("No te escuché bien, ¿me puedes repetir?")
                        continue
                    else:
                        break
            if response == "exit":
                break
            elif response == "":
                continue

            print(response)
            speak(response)
    except KeyboardInterrupt:
        pass
    finally:
        print("Done.")
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
