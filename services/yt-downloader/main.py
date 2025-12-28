import argparse
import os
from downloader import download_video, download_subtitles

def main():
    """
    Main function to parse arguments and initiate downloads.
    """
    parser = argparse.ArgumentParser(description="YouTube Media Downloader")
    parser.add_argument("url", help="The URL of the YouTube video.")
    parser.add_argument("--no-video", action="store_true", help="Do not download the video.")
    parser.add_argument("--no-subs", action="store_true", help="Do not download subtitles.")
    
    args = parser.parse_args()

    output_dir = "downloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    if not args.no_video:
        download_video(args.url, output_template)
    
    if not args.no_subs:
        download_subtitles(args.url, output_template)

if __name__ == "__main__":
    main()
