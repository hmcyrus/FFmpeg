/**
 * Hello FFmpeg - Java Edition
 *
 * Java does not have a standard FFmpeg binding the way Python has PyAV,
 * so this example uses the ffmpeg COMMAND-LINE TOOL via ProcessBuilder.
 * This is the most common real-world Java approach for video work.
 *
 * What this does:
 *   1. Uses ffmpeg to generate a synthetic test video (color bars + tone)
 *   2. Then probes the output file with ffprobe to read back its metadata
 *
 * C concepts this maps to:
 *   avformat_open_input  -> "ffmpeg -i ..."          reads/opens input
 *   AVCodecContext       -> "-c:v mpeg4 -b:v 400k"   codec + settings
 *   AVFrame (video)      -> "lavfi" test sources      synthetic frames
 *   av_write_trailer     -> ffmpeg closes file cleanly on success
 *
 * Requirements: ffmpeg and ffprobe must be on your PATH.
 *   Ubuntu/Debian: sudo apt install ffmpeg
 *   Mac:           brew install ffmpeg
 */

import java.io.*;
import java.util.*;

public class HelloFFmpeg {

    // ---------------------------------------------------------------------------
    // Equivalent to AVCodecContext settings in encode_video.c:
    //   c->width = 320; c->height = 240;
    //   c->time_base = (AVRational){1,25}; c->framerate = (AVRational){25,1};
    //   c->bit_rate = 400000;
    // ---------------------------------------------------------------------------
    private static final int    WIDTH      = 320;
    private static final int    HEIGHT     = 240;
    private static final int    FPS        = 25;
    private static final int    DURATION_S = 2;    // seconds
    private static final String CODEC      = "mpeg4";
    private static final String OUTPUT     = "output.mp4";

    public static void main(String[] args) throws Exception {

        // -----------------------------------------------------------------------
        // Step 1: Encode - generate a synthetic video using the ffmpeg CLI.
        //
        // "lavfi" is FFmpeg's "libavfilter virtual input" device.
        // "testsrc" is a built-in source that generates color-bar test frames —
        // the same thing the C encode_video.c does manually with nested loops
        // filling frame->data[0/1/2] with synthetic pixel values.
        //
        // The command below is the CLI equivalent of:
        //   avformat_alloc_output_context2(...)
        //   avcodec_find_encoder_by_name("mpeg4")
        //   avcodec_open2(...)
        //   for each frame: avcodec_send_frame + avcodec_receive_packet
        //   av_write_trailer(...)
        // -----------------------------------------------------------------------
        System.out.println("=== Step 1: Encoding synthetic video ===");
        List<String> encodeCmd = List.of(
            "ffmpeg",
            "-y",                                   // overwrite output without asking
            "-f",  "lavfi",                         // input format: virtual filter device
            "-i",  "testsrc=size=" + WIDTH + "x" + HEIGHT + ":rate=" + FPS,
            "-t",  String.valueOf(DURATION_S),      // duration in seconds
            "-c:v", CODEC,                          // video codec (AVCodecContext)
            "-b:v", "400k",                         // bitrate (c->bit_rate = 400000)
            "-pix_fmt", "yuv420p",                  // pixel format (AV_PIX_FMT_YUV420P)
            OUTPUT
        );

        runCommand(encodeCmd, "Encoding");

        // -----------------------------------------------------------------------
        // Step 2: Probe - read back the file's metadata.
        //
        // This maps to avformat_open_input + avformat_find_stream_info in C,
        // which is what FFmpeg uses internally to detect codecs, duration,
        // resolution etc. from the container headers.
        // -----------------------------------------------------------------------
        System.out.println("\n=== Step 2: Probing output file metadata ===");
        List<String> probeCmd = List.of(
            "ffprobe",
            "-v", "quiet",          // suppress banner
            "-show_format",         // print [FORMAT] section  (avformat_find_stream_info)
            "-show_streams",        // print [STREAM] sections (AVCodecParameters)
            "-pretty",              // human-readable sizes and durations
            OUTPUT
        );

        runCommand(probeCmd, "Probing");

        System.out.println("\nDone! File written: " + OUTPUT);
    }

    /**
     * Run an external command, stream its output to stdout/stderr line-by-line,
     * and throw if it exits with a non-zero code.
     *
     * In real production code you would use a library like:
     *   - Jaffree  (pure Java ffmpeg wrapper, idiomatic)
     *   - JavaCV   (JNI binding to libav*, closest to the raw C API)
     */
    private static void runCommand(List<String> cmd, String label) throws Exception {
        System.out.println("Running: " + String.join(" ", cmd));

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);   // merge stderr into stdout
        Process process = pb.start();

        // Stream output in real time
        try (BufferedReader reader =
                new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("  [" + label + "] " + line);
            }
        }

        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new RuntimeException(label + " failed with exit code " + exitCode);
        }
    }
}
