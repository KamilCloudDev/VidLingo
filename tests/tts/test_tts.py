import unittest
import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch

# Dodaj katalog services do ścieżki Pythona, aby móc importować moduły
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/tts')))

from tts import find_voice_for_language, generate_segment_audio, get_audio_duration, apply_atempo

# Mock dla klasy Communicate z edge_tts
class MockCommunicate:
    def __init__(self, text, voice):
        self.text = text
        self.voice = voice

    async def save(self, output_path):
        # Symulacja zapisu pliku
        with open(output_path, 'w') as f:
            f.write(f"dummy audio for '{self.text}'")
        # Symulacja rozmiaru pliku
        self.saved_size = len(f"dummy audio for '{self.text}'") * 2 # Aby był > 100 bajtów dla walidacji

class TestTtsFunctions(unittest.IsolatedAsyncioTestCase):

    @patch('tts.edge_tts.list_voices')
    async def test_find_voice_for_language_polish(self, mock_list_voices):
        mock_list_voices.return_value = [
            {'ShortName': 'en-US-Standard-A', 'Gender': 'Female', 'Locale': 'en-US'},
            {'ShortName': 'pl-PL-MarekNeural', 'Gender': 'Male', 'Locale': 'pl-PL', 'Name': 'pl-PL-MarekNeural'},
            {'ShortName': 'de-DE-Standard-B', 'Gender': 'Male', 'Locale': 'de-DE'},
        ]
        result = await find_voice_for_language("Polish")
        self.assertEqual(result, "pl-PL-MarekNeural")

    @patch('tts.edge_tts.list_voices')
    async def test_find_voice_for_language_english_default(self, mock_list_voices):
        mock_list_voices.return_value = [
            {'ShortName': 'fr-FR-Standard-A', 'Gender': 'Female', 'Locale': 'fr-FR'},
        ]
        result = await find_voice_for_language("NonExistentLanguage")
        self.assertEqual(result, "en-US-ChristopherNeural")
        
    @patch('tts.edge_tts.list_voices')
    async def test_find_voice_for_language_english_male_neural(self, mock_list_voices):
        mock_list_voices.return_value = [
            {'ShortName': 'en-US-ChristopherNeural', 'Gender': 'Male', 'Locale': 'en-US', 'Name': 'en-US-ChristopherNeural'},
            {'ShortName': 'en-US-GuyNeural', 'Gender': 'Male', 'Locale': 'en-US', 'Name': 'en-US-GuyNeural'},
            {'ShortName': 'en-GB-Standard-A', 'Gender': 'Female', 'Locale': 'en-GB'},
        ]
        result = await find_voice_for_language("English")
        self.assertIn(result, ['en-US-ChristopherNeural', 'en-US-GuyNeural']) # Może wybrać dowolny męski Neural

    @patch('tts.os.path.exists', return_value=True)
    @patch('tts.os.path.getsize', return_value=500) # Ensure size > 100 for validation
    @patch('tts.get_audio_duration', side_effect=[2.0, 1.8]) # Mock for current_dur and after speedup
    @patch('tts.apply_atempo', new_callable=AsyncMock)
    @patch('tts.edge_tts.Communicate', new=MockCommunicate)
    async def test_generate_segment_audio_with_speedup(self, mock_apply_atempo, mock_get_audio_duration, mock_getsize, mock_exists):
        output_path = "temp_audio.mp3"
        text = "This is a test sentence."
        voice = "en-US-ChristopherNeural"
        target_duration = 1.5

        await generate_segment_audio(text, voice, output_path, target_duration=target_duration)

        mock_apply_atempo.assert_called_once()
        self.assertTrue(os.path.exists(output_path))
        os.remove(output_path) # Clean up dummy file

    @patch('tts.os.path.exists', return_value=False)
    @patch('tts.AudioSegment.silent')
    @patch('tts.edge_tts.Communicate', new=MockCommunicate)
    async def test_generate_segment_audio_empty_text(self, mock_silent, mock_exists):
        output_path = "temp_audio_silent.mp3"
        text = ""
        voice = "en-US-ChristopherNeural"
        target_duration = 2.0

        await generate_segment_audio(text, voice, output_path, target_duration=target_duration)
        
        mock_silent.assert_called_once_with(duration=int(target_duration * 1000))
        # Ensure a dummy file is created by our MockCommunicate, but silent takes precedence
        # We need to manually remove the dummy file if it was created by MockCommunicate's save
        if os.path.exists(output_path):
            os.remove(output_path)

    @patch('tts.os.path.exists', return_value=True)
    @patch('tts.os.path.getsize', side_effect=[50, 500]) # First try fails size check, second succeeds
    @patch('tts.get_audio_duration', return_value=1.0)
    @patch('tts.apply_atempo', new_callable=AsyncMock)
    @patch('tts.edge_tts.Communicate', new=MockCommunicate)
    @patch('tts.asyncio.sleep', new_callable=AsyncMock)
    async def test_generate_segment_audio_retry_mechanism(self, mock_sleep, mock_apply_atempo, mock_get_audio_duration, mock_getsize, mock_exists):
        output_path = "temp_audio_retry.mp3"
        text = "This should retry."
        voice = "en-US-ChristopherNeural"
        target_duration = 1.0

        await generate_segment_audio(text, voice, output_path, target_duration=target_duration, retries=2)
        
        # Expect sleep to be called once after the first failed attempt
        mock_sleep.assert_called_once()
        self.assertTrue(os.path.exists(output_path))
        os.remove(output_path) # Clean up dummy file


if __name__ == '__main__':
    unittest.main()
