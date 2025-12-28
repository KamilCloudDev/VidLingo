import yt_dlp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_video(video_url: str, output_path: str = 'downloads/%(title)s.%(ext)s'):
    """
    Downloads a video from the given URL in the best available MP4 format.

    :param video_url: The URL of the video to download.
    :param output_path: The output template for the downloaded file.
    """
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Starting video download for: {video_url}")
            ydl.download([video_url])
            logging.info(f"Successfully downloaded video: {video_url}")
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading video: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def download_subtitles(video_url: str, output_path: str = 'downloads/%(title)s.%(ext)s'):
    """
    Checks for and downloads available subtitles (SRT/VTT) for the given video URL.

    :param video_url: The URL of the video.
    :param output_path: The output template for the downloaded subtitle file.
    """
    ydl_opts = {
        'writesubtitles': True,
        'subtitlesformat': 'srt/vtt',
        'skip_download': True, # We only want subtitles
        'outtmpl': output_path,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            if info_dict.get('subtitles') or info_dict.get('automatic_captions'):
                logging.info(f"Found subtitles for {video_url}. Starting download.")
                ydl.download([video_url])
                logging.info(f"Successfully downloaded subtitles for {video_url}")
            else:
                logging.warning(f"No subtitles found for {video_url}")
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading subtitles: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
