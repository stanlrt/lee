import { GoogleGenerativeAI } from '@google/generative-ai';
import { logger } from './logger.js';
import { readEnvFile } from './env.js';

export async function transcribeAudio(
  audioBuffer: Buffer,
  mimeType: string,
): Promise<string> {
  const apiKey =
    process.env.GEMINI_API_KEY ||
    readEnvFile(['GEMINI_API_KEY']).GEMINI_API_KEY;
  if (!apiKey) {
    logger.warn('GEMINI_API_KEY not set — voice transcription unavailable');
    return '[Voice message — transcription unavailable]';
  }

  try {
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

    const result = await model.generateContent([
      {
        inlineData: {
          data: audioBuffer.toString('base64'),
          mimeType,
        },
      },
      'Transcribe this voice message. Return only the transcript text, nothing else.',
    ]);

    const transcript = result.response.text().trim();
    logger.info({ chars: transcript.length }, 'Transcribed voice message');
    return transcript;
  } catch (err) {
    logger.error({ err }, 'Gemini transcription failed');
    return '[Voice message — transcription failed]';
  }
}
