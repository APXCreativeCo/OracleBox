#ifndef MELODIES_H
#define MELODIES_H

// Note definitions (frequencies in Hz)
#define NOTE_C4  262
#define NOTE_D4  294
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_G4  392
#define NOTE_A4  440
#define NOTE_B4  494
#define NOTE_C5  523
#define NOTE_D5  587
#define NOTE_E5  659
#define NOTE_F5  698
#define NOTE_G5  784
#define NOTE_A5  880
#define NOTE_B5  988
#define NOTE_C6  1047

// Duration definitions (in milliseconds)
#define WHOLE_NOTE 1600
#define HALF_NOTE 800
#define QUARTER_NOTE 400
#define EIGHTH_NOTE 200

// Twinkle Twinkle Little Star
const int melody_twinkle_star[] = {
  NOTE_C5, NOTE_C5, NOTE_G5, NOTE_G5, NOTE_A5, NOTE_A5, NOTE_G5,
  NOTE_F5, NOTE_F5, NOTE_E5, NOTE_E5, NOTE_D5, NOTE_D5, NOTE_C5
};
const int durations_twinkle_star[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, 
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, 
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE
};
const int melody_twinkle_length = 14;

// Brahms Lullaby (creepy version - slower)
const int melody_lullaby[] = {
  NOTE_G4, NOTE_G4, NOTE_A4, NOTE_G4, NOTE_C5, NOTE_B4,
  NOTE_G4, NOTE_G4, NOTE_A4, NOTE_G4, NOTE_D5, NOTE_C5
};
const int durations_lullaby[] = {
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE, HALF_NOTE, HALF_NOTE, WHOLE_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE, HALF_NOTE, HALF_NOTE, WHOLE_NOTE
};
const int melody_lullaby_length = 12;

// Carousel/Music Box (repetitive creepy tune)
const int melody_carousel[] = {
  NOTE_C5, NOTE_E5, NOTE_G5, NOTE_C6, NOTE_G5, NOTE_E5,
  NOTE_D5, NOTE_F5, NOTE_A5, NOTE_D5, NOTE_A5, NOTE_F5,
  NOTE_E5, NOTE_G5, NOTE_C6, NOTE_E5, NOTE_C6, NOTE_G5
};
const int durations_carousel[] = {
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE, EIGHTH_NOTE, EIGHTH_NOTE,
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE, EIGHTH_NOTE, EIGHTH_NOTE,
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE, EIGHTH_NOTE, QUARTER_NOTE
};
const int melody_carousel_length = 18;

#endif
