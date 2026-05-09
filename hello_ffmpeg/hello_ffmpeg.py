"""
Hello FFmpeg - Python Edition
Uses PyAV (pip install av), which is a thin Python wrapper around the same
C libraries (libavformat, libavcodec, libavutil) you see in the FFmpeg source.

What this does:
  1. Creates a synthetic "rainbow bars" video in memory (no input file needed)
  2. Encodes it to MPEG-4 video
  3. Saves it as output.mp4

C concepts translated to Python:
  AVFormatContext  -> av.open(...)          (the container: MP4, MKV, etc.)
  AVCodecContext   -> stream.codec_context  (the encoder settings)
  AVFrame          -> av.VideoFrame         (one decoded image)
  AVPacket         -> yielded automatically by encode()
  avcodec_send_frame / avcodec_receive_packet -> frame.encode() in PyAV
"""

import av
import numpy as np

OUTPUT_FILE = "output.mp4"
WIDTH = 320
HEIGHT = 240
FPS = 25
NUM_FRAMES = 50  # 2 seconds of video


def make_rainbow_frame(frame_index: int, width: int, height: int) -> np.ndarray:
    """
    Build one frame of pixel data as a NumPy array (shape: height x width x 3, dtype uint8).
    This is the equivalent of the nested x/y loops in encode_video.c that fill
    frame->data[0] (Y plane) and frame->data[1/2] (Cb/Cr planes).
    We work in RGB here; PyAV converts to YUV420P automatically.
    """
    # Each column gets a different hue, shifting over time
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        hue = (x + frame_index * 5) % 256   # shift right every frame
        img[:, x, 0] = hue                   # R channel
        img[:, x, 1] = 255 - hue            # G channel
        img[:, x, 2] = (hue * 2) % 256      # B channel
    return img


def main():
    # -------------------------------------------------------------------------
    # Step 1: Open an output container
    # C equivalent: avformat_alloc_output_context2(&fmt_ctx, NULL, NULL, filename)
    #               avio_open(&fmt_ctx->pb, filename, AVIO_FLAG_WRITE)
    # The format (MP4) is inferred from the filename extension.
    # -------------------------------------------------------------------------
    container = av.open(OUTPUT_FILE, mode="w")
    print(f"Opened container: {OUTPUT_FILE}")

    # -------------------------------------------------------------------------
    # Step 2: Add a video stream with a codec
    # C equivalent: avcodec_find_encoder(AV_CODEC_ID_MPEG4)
    #               avformat_new_stream(fmt_ctx, codec)
    #               avcodec_alloc_context3(codec)
    # -------------------------------------------------------------------------
    stream = container.add_stream("mpeg4", rate=FPS)
    stream.width = WIDTH
    stream.height = HEIGHT
    stream.pix_fmt = "yuv420p"          # standard pixel format for compatibility
    #   In encode_video.c: c->pix_fmt = AV_PIX_FMT_YUV420P
    stream.bit_rate = 400_000           # 400 kbps, same as the C example

    # -------------------------------------------------------------------------
    # Step 3: Open the codec (lock in the settings)
    # C equivalent: avcodec_open2(c, codec, NULL)
    # PyAV does this lazily when you first encode, but we can trigger it now.
    # -------------------------------------------------------------------------
    codec_ctx = stream.codec_context
    print(f"Codec: {codec_ctx.name}, {WIDTH}x{HEIGHT} @ {FPS}fps")

    # -------------------------------------------------------------------------
    # Step 4: Encode frames
    # C equivalent (from encode_video.c):
    #   for (i = 0; i < 25; i++) {
    #       av_frame_make_writable(frame);
    #       /* fill frame->data[0..2] */
    #       frame->pts = i;
    #       encode(c, frame, pkt, f);   // avcodec_send_frame + avcodec_receive_packet
    #   }
    # -------------------------------------------------------------------------
    for i in range(NUM_FRAMES):
        # Build raw pixel data
        rgb_array = make_rainbow_frame(i, WIDTH, HEIGHT)

        # Wrap it in an AVFrame (PyAV calls this VideoFrame)
        # C: av_frame_alloc() + manually fill frame->data planes
        frame = av.VideoFrame.from_ndarray(rgb_array, format="rgb24")
        frame.pts = i   # presentation timestamp: which frame number this is

        # Encode: send frame to codec, receive compressed packet(s)
        # C: avcodec_send_frame(enc_ctx, frame)
        #    while avcodec_receive_packet(enc_ctx, pkt) == 0: fwrite(...)
        for packet in stream.encode(frame):
            container.mux(packet)   # write compressed packet into the MP4 container

        if i % 10 == 0:
            print(f"  Encoded frame {i}/{NUM_FRAMES}")

    # -------------------------------------------------------------------------
    # Step 5: Flush the encoder (drain buffered frames)
    # C equivalent: encode(c, NULL, pkt, f)  — passing NULL flushes
    # Some codecs buffer several frames before outputting packets (B-frames, etc.)
    # -------------------------------------------------------------------------
    for packet in stream.encode():   # no argument = flush
        container.mux(packet)

    # -------------------------------------------------------------------------
    # Step 6: Write the container trailer and close
    # C equivalent: av_write_trailer(fmt_ctx)
    #               avio_closep(&fmt_ctx->pb)
    #               avformat_free_context(fmt_ctx)
    # -------------------------------------------------------------------------
    container.close()
    print(f"\nDone! Written {NUM_FRAMES} frames to {OUTPUT_FILE}")
    print("Play with: ffplay output.mp4  OR  vlc output.mp4")


if __name__ == "__main__":
    main()
