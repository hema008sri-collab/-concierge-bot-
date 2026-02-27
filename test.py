from langdetect import detect, detect_langs

text = "Bonjour tout le monde"
print(detect(text))        # Expected output: 'fr'
print(detect_langs(text))  # Shows probabilities