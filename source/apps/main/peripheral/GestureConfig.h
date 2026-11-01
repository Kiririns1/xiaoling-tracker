#pragma once
#include <stdint.h>
static constexpr int YAW_PIN=5,PITCH_PIN=6;
static constexpr int SERVO_NEUTRAL[2]={1500,1500};
static constexpr int SERVO_MIN_OFFSET[2]={40,40};
static constexpr int SERVO_MAX_OFFSET[2]={120,120};
static constexpr float SERVO_MAX_SPEED=.35f;
// Compatibility field carries direction only; follow PWM is fixed at +/-75us.
static constexpr float HAND_FOLLOW_MAX_SPEED=.03f;

// Previous nod: .06 normalized (~53us), 120ms down / 120ms pause / 120ms up.
// Slower and longer: .025 (~45us), 300ms down / 200ms pause / 300ms up.
static constexpr float FIST_NOD_SPEED=.025f;
static constexpr uint32_t FIST_NOD_STROKE_MS=300,FIST_NOD_PAUSE_MS=200,FIST_NOD_SETTLE_MS=200;
