#!/usr/bin/env python3
"""
Audio Watermarking using LSB (Least Significant Bit) Steganography

This script implements a simple audio watermarking system that can:
1. Embed a text message into a WAV audio file using LSB modification
2. Extract the hidden message from a watermarked audio file

The watermarking is done by modifying the least significant bits of audio samples
to encode binary data representing the text message.
"""

import numpy as np
import wave
import struct
import sys


def text_to_binary(text):
    """
    Convert text to binary string representation.
    
    Args:
        text (str): The text message to convert
        
    Returns:
        str: Binary string representation of the text
    """
    binary = ""
    for char in text:
        # Convert each character to 8-bit binary
        binary += format(ord(char), '08b')
    return binary


def binary_to_text(binary):
    """
    Convert binary string back to text.
    
    Args:
        binary (str): Binary string representation
        
    Returns:
        str: The original text message
    """
    text = ""
    # Process 8 bits at a time
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) == 8:
            text += chr(int(byte, 2))
    return text


def embed_message(input_wav, output_wav, message):
    """
    Embed a text message into an audio file using LSB steganography.
    
    Args:
        input_wav (str): Path to the input WAV file
        output_wav (str): Path to save the watermarked WAV file
        message (str): The text message to embed
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the input WAV file
        with wave.open(input_wav, 'rb') as audio_file:
            # Get audio parameters
            frames = audio_file.getnframes()
            sample_rate = audio_file.getframerate()
            channels = audio_file.getnchannels()
            sample_width = audio_file.getsampwidth()
            
            # Read all audio data
            audio_data = audio_file.readframes(frames)
            
        # Convert audio data to numpy array for easier manipulation
        if sample_width == 1:
            # 8-bit audio
            audio_array = np.frombuffer(audio_data, dtype=np.uint8).copy()
        elif sample_width == 2:
            # 16-bit audio - keep as int16 and work with raw bytes
            audio_array = np.frombuffer(audio_data, dtype=np.int16).copy()
        elif sample_width == 4:
            # 32-bit audio
            audio_array = np.frombuffer(audio_data, dtype=np.int32).copy()
        else:
            print(f"Unsupported sample width: {sample_width}")
            return False
            
        # Convert message to binary
        message_binary = text_to_binary(message)
        
        # Add a delimiter to mark the end of the message (16 zeros)
        message_binary += "0000000000000000"
        
        # For multi-channel audio, only embed in the first channel
        samples_per_channel = len(audio_array) // channels
        if len(message_binary) > samples_per_channel:
            print("Error: Message too long for the audio file")
            return False
            
        # Embed the message using LSB modification (only in first channel)
        for i, bit in enumerate(message_binary):
            # Only modify samples from the first channel
            sample_index = i * channels
            if sample_index < len(audio_array):
                # Modify the least significant bit of each audio sample
                if sample_width == 1:
                    # For 8-bit audio
                    audio_array[sample_index] = (audio_array[sample_index] & 0xFE) | int(bit)
                elif sample_width == 2:
                    # For 16-bit audio - use numpy's view to handle signed/unsigned conversion
                    current_val = audio_array[sample_index]
                    # Convert to unsigned for bit manipulation
                    unsigned_val = current_val.astype(np.uint16)
                    if int(bit) == 0:
                        # Set LSB to 0
                        new_unsigned = unsigned_val & 0xFFFE
                    else:
                        # Set LSB to 1
                        new_unsigned = unsigned_val | 0x0001
                    
                    # Convert back to signed int16 using numpy
                    audio_array[sample_index] = new_unsigned.astype(np.int16)
                elif sample_width == 4:
                    # For 32-bit audio
                    audio_array[sample_index] = (audio_array[sample_index] & 0xFFFFFFFE) | int(bit)
            else:
                print(f"Warning: Not enough samples to embed bit {i}")
                break
        
        # Convert back to bytes
        if sample_width == 1:
            watermarked_data = audio_array.astype(np.uint8).tobytes()
        elif sample_width == 2:
            # Keep as int16
            watermarked_data = audio_array.astype(np.int16).tobytes()
        elif sample_width == 4:
            watermarked_data = audio_array.astype(np.int32).tobytes()
        
        # Write the watermarked audio to output file
        with wave.open(output_wav, 'wb') as output_file:
            output_file.setnchannels(channels)
            output_file.setsampwidth(sample_width)
            output_file.setframerate(sample_rate)
            output_file.writeframes(watermarked_data)
            
        print(f"Message successfully embedded in {output_wav}")
        return True
        
    except Exception as e:
        print(f"Error embedding message: {e}")
        return False


def extract_message(watermarked_wav):
    """
    Extract a hidden text message from a watermarked audio file.
    
    Args:
        watermarked_wav (str): Path to the watermarked WAV file
        
    Returns:
        str: The extracted text message, or empty string if extraction fails
    """
    try:
        # Read the watermarked WAV file
        with wave.open(watermarked_wav, 'rb') as audio_file:
            # Get audio parameters
            frames = audio_file.getnframes()
            sample_width = audio_file.getsampwidth()
            channels = audio_file.getnchannels()
            
            # Read all audio data
            audio_data = audio_file.readframes(frames)
            
        # Convert audio data to numpy array
        if sample_width == 1:
            # 8-bit audio
            audio_array = np.frombuffer(audio_data, dtype=np.uint8).copy()
        elif sample_width == 2:
            # 16-bit audio - use int16 to match embedding
            audio_array = np.frombuffer(audio_data, dtype=np.int16).copy()
        elif sample_width == 4:
            # 32-bit audio
            audio_array = np.frombuffer(audio_data, dtype=np.int32).copy()
        else:
            print(f"Unsupported sample width: {sample_width}")
            return ""
            
        # Extract LSBs from audio samples (only from first channel)
        binary_message = ""
        samples_per_channel = len(audio_array) // channels
        
        # Extract bits until we find the delimiter
        # We'll extract from all available samples in the first channel
        for i in range(samples_per_channel):
            # Only extract from the first channel
            sample_index = i * channels
            if sample_index < len(audio_array):
                sample = audio_array[sample_index]
                # Extract the least significant bit
                bit = sample & 0x01
                binary_message += str(bit)
                
                # Check for delimiter (16 consecutive zeros) - but only after we have enough bits
                if len(binary_message) >= 16:
                    # Look for the delimiter pattern
                    last_16 = binary_message[-16:]
                    if last_16 == "0000000000000000":
                        # Remove the delimiter
                        binary_message = binary_message[:-16]
                        break
            else:
                break
        
        # If we didn't find the delimiter, try to find a valid 8-bit boundary
        if len(binary_message) % 8 != 0:
            # Try to find a valid 8-bit boundary by removing extra bits
            for i in range(8):
                if (len(binary_message) - i) % 8 == 0:
                    binary_message = binary_message[:len(binary_message) - i]
                    break
                
        # Convert binary back to text
        if len(binary_message) % 8 != 0:
            print(f"Error: Invalid binary data length: {len(binary_message)}")
            print(f"Binary data: {binary_message}")
            return ""
            
        message = binary_to_text(binary_message)
        return message
        
    except Exception as e:
        print(f"Error extracting message: {e}")
        return ""


def main():
    """
    Main function to demonstrate the audio watermarking functionality.
    """
    print("Audio Watermarking Demo")
    print("=" * 30)
    
    # Example usage
    input_file = "input.wav"
    output_file = "watermarked.wav"
    message = "Hi I Mahdi, It is a secret message!"
    
    print(f"Original message: {message}")
    print(f"Message length: {len(message)} characters ({len(message) * 8} bits)")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Check if input file exists
    try:
        with open(input_file, 'rb'):
            pass
    except FileNotFoundError:
        print(f"\nError: Input file '{input_file}' not found.")
        print("Please provide a WAV audio file named 'input.wav' in the current directory.")
        print("\nYou can create a test audio file using:")
        print("1. Record audio using any audio recording software")
        print("2. Convert to WAV format")
        print("3. Save as 'input.wav' in this directory")
        return
    
    # Embed the message
    print(f"\nEmbedding message into audio...")
    if embed_message(input_file, output_file, message):
        print("✓ Message embedded successfully!")
        
        # Extract the message to verify
        print(f"\nExtracting message from watermarked audio...")
        extracted_message = extract_message(output_file)
        
        if extracted_message:
            print(f"✓ Extracted message: '{extracted_message}'")
            
            # Verify the message
            if extracted_message == message:
                print("✓ Message verification successful!")
            else:
                print("✗ Message verification failed!")
        else:
            print("✗ Failed to extract message!")
    else:
        print("✗ Failed to embed message!")


if __name__ == "__main__":
    main()
