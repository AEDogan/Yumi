"""Bounded OpenAI requests. All calls are made off the UI thread."""
from __future__ import annotations

import io
import os
import wave

import numpy as np
import requests

BASE = 'https://api.openai.com/v1'


def _post(key: str, endpoint: str, **kwargs):
    if not key:
        raise ValueError('Önce ayarlardan OpenAI API anahtarını girin.')
    response = requests.post(f'{BASE}/{endpoint}', headers={'Authorization': f'Bearer {key}'},
                             timeout=60, **kwargs)
    if not response.ok:
        try:
            message = response.json()['error']['message']
        except (ValueError, KeyError, TypeError):
            message = f'API hatası ({response.status_code})'
        raise RuntimeError(message)
    return response


def transcribe(key: str, samples: np.ndarray) -> str:
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(np.clip(samples * 32767, -32768, 32767).astype('<i2').tobytes())
    result = _post(key, 'audio/transcriptions', files={'file': ('voice.wav', buffer.getvalue(), 'audio/wav')},
                   data={'model': 'gpt-transcribe'}).json()
    return result.get('text', '').strip()


def answer(key: str, text: str, previous_id: str | None = None, model='gpt-5.4-mini',history=()) -> tuple[str, str]:
    payload = {'model': model, 'input': text[:4000], 'store': True,
               'instructions': 'Sen Yumi adlı Türkçe konuşan bir masaüstü asistanısın. Ahmet ile doğal gündelik Türkçe konuş. Varsayılan yanıtı bir veya iki kısa cümle tut; ayrıntı istenirse genişlet. Kendiliğinden tarih, kaynak adı veya gereksiz teknik bilgi sayma. Doğrudan yanıt ver; yanıt uzunluğunu soruya göre ayarla. Kelime kelime çeviri gibi ifadeler, gereksiz selamlar ve kalıp girişler kullanma. Takip sorularını konuşma bağlamıyla birlikte değerlendir. Metin sesli okunacağı için Markdown, tablo ve emoji kullanma. Bilgisayarda işlem yaptığını iddia etme; masaüstü etkinliği yalnızca karakter animasyonları için kullanılıyor.'}
    if previous_id:
        payload['previous_response_id'] = previous_id
    elif history:
        payload['input']=[{'role':m['role'],'content':m['text']} for m in history[-16:]]+[{'role':'user','content':text[:4000]}]
    result = _post(key, 'responses', json=payload).json()
    parts = [content.get('text', '') for item in result.get('output', [])
             for content in item.get('content', []) if content.get('type') == 'output_text']
    return '\n'.join(parts).strip() or 'Yanıt alınamadı.', result['id']


def speech(key: str, text: str, voice: str = 'coral') -> bytes:
    payload = {'model': 'gpt-4o-mini-tts', 'voice': voice, 'input': text[:1200],
               'instructions': 'Türkçe, doğal, sıcak ve canlı bir ses tonuyla konuş.'}
    return _post(key, 'audio/speech', json=payload).content
