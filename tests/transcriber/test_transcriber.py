import unittest
import sys
import os

# Dodaj katalog services do ścieżki Pythona, aby móc importować moduły
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/transcriber')))

from transcriber import regroup_words_into_segments

# Klasa MockWord do emulacji zachowania słowa z faster-whisper
class MockWord:
    def __init__(self, word, start, end, probability):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability

# Klasa MockSegment do emulacji zachowania segmentu z faster-whisper
class MockSegment:
    def __init__(self, words_data):
        self.words = [MockWord(**data) for data in words_data]

class TestTranscriberFunctions(unittest.TestCase):

    def test_regroup_words_into_segments_simple(self):
        # Prosty przypadek: słowa, które można łatwo pogrupować w segmenty
        # Tworzymy mockowe segmenty, tak jak zwraca faster-whisper
        mock_segments_input = [
            MockSegment([
                {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'probability': 0.9},
                {'word': 'world.', 'start': 0.6, 'end': 1.0, 'probability': 0.9},
            ]),
            MockSegment([
                {'word': 'How', 'start': 1.5, 'end': 1.8, 'probability': 0.9},
                {'word': 'are', 'start': 1.9, 'end': 2.1, 'probability': 0.9},
                {'word': 'you?', 'start': 2.2, 'end': 2.5, 'probability': 0.9},
            ])
        ]
        expected_segments = [
            {'text': 'Hello world.', 'start': 0.0, 'end': 1.0},
            {'text': 'How are you?', 'start': 1.5, 'end': 2.5},
        ]
        result = list(regroup_words_into_segments(mock_segments_input))
        self.assertEqual(len(result), len(expected_segments))
        for i in range(len(result)):
            self.assertAlmostEqual(result[i]['start'], expected_segments[i]['start'], places=2)
            self.assertAlmostEqual(result[i]['end'], expected_segments[i]['end'], places=2)
            self.assertEqual(result[i]['text'], expected_segments[i]['text'])

    def test_regroup_words_into_segments_with_long_pause(self):
        # Przypadek z dłuższą pauzą, która powinna utworzyć nowy segment
        mock_segments_input = [
            MockSegment([
                {'word': 'First', 'start': 0.0, 'end': 0.5, 'probability': 0.9},
                {'word': 'segment.', 'start': 0.6, 'end': 1.0, 'probability': 0.9},
            ]),
            MockSegment([
                {'word': 'Second', 'start': 5.0, 'end': 5.5, 'probability': 0.9}, # Duża przerwa
                {'word': 'segment.', 'start': 5.6, 'end': 6.0, 'probability': 0.9},
            ])
        ]
        expected_segments = [
            {'text': 'First segment.', 'start': 0.0, 'end': 1.0},
            {'text': 'Second segment.', 'start': 5.0, 'end': 6.0},
        ]
        result = list(regroup_words_into_segments(mock_segments_input))
        self.assertEqual(len(result), len(expected_segments))
        for i in range(len(result)):
            self.assertAlmostEqual(result[i]['start'], expected_segments[i]['start'], places=2)
            self.assertAlmostEqual(result[i]['end'], expected_segments[i]['end'], places=2)
            self.assertEqual(result[i]['text'], expected_segments[i]['text'])

    def test_regroup_words_into_segments_empty_input(self):
        # Pusty przypadek wejściowy
        mock_segments_input = []
        expected_segments = []
        result = list(regroup_words_into_segments(mock_segments_input))
        self.assertEqual(result, expected_segments)

    def test_regroup_words_into_segments_single_word(self):
        # Pojedyncze słowo
        mock_segments_input = [
            MockSegment([
                {'word': 'Onlyword.', 'start': 0.0, 'end': 0.8, 'probability': 0.9},
            ])
        ]
        expected_segments = [
            {'text': 'Onlyword.', 'start': 0.0, 'end': 0.8},
        ]
        result = list(regroup_words_into_segments(mock_segments_input))
        self.assertEqual(len(result), len(expected_segments))
        self.assertAlmostEqual(result[0]['start'], expected_segments[0]['start'], places=2)
        self.assertAlmostEqual(result[0]['end'], expected_segments[0]['end'], places=2)
        self.assertEqual(result[0]['text'], expected_segments[0]['text'])

if __name__ == '__main__':
    unittest.main()
