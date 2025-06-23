# European Rover Challenge (ERC) Visual Style Guide

## Theme Overview
Inspired by the European Rover Challenge poster featuring Mars exploration and rover technology. The design captures the essence of space exploration with a retro sci-fi aesthetic reminiscent of vintage NASA posters.

## Color Palette

### Primary Colors
- **Mars Orange**: `#FF6B35` - Dominant background color representing the Martian atmosphere
- **Deep Mars**: `#E55100` - Darker orange for depth and shadows
- **Martian Sunset**: `#FF8F65` - Lighter orange for highlights

### Secondary Colors
- **Space Black**: `#1A1A1A` - Deep space backgrounds and UI elements
- **Rover Dark**: `#2D2D2D` - Dark metallic surfaces and machinery
- **Shadow Brown**: `#3E2723` - Warm shadows and depth

### Accent Colors
- **Mission Yellow**: `#FFB300` - Warning indicators, active states, highlights
- **System Green**: `#4CAF50` - Success states, active sensors, operational indicators
- **Alert Red**: `#F44336` - Error states, safety warnings, critical alerts
- **Tech Blue**: `#2196F3` - Information displays, data streams, cool technology

### Text Colors
- **Primary Text**: `#FFFFFF` - Main text on dark backgrounds
- **Secondary Text**: `#CCCCCC` - Subtle text and descriptions
- **Inverse Text**: `#1A1A1A` - Text on light backgrounds

## Typography

### Font Families
- **Primary**: Arial, Helvetica, sans-serif - Clean, technical readability
- **Monospace**: Consolas, Courier New, monospace - Terminal and data displays
- **Headers**: Arial Black, Impact - Bold mission-critical information

### Font Weights
- **Light**: 300 - Subtle information
- **Regular**: 400 - Standard text
- **Bold**: 700 - Important labels and status
- **Extra Bold**: 900 - Critical alerts and headers

## Visual Elements

### Gradients
- **Mars Atmosphere**: Linear gradient from `#FF6B35` to `#E55100`
- **Deep Space**: Radial gradient from `#2D2D2D` to `#1A1A1A`
- **Sunset Horizon**: Linear gradient from `#FFB300` to `#FF6B35`

### Shadows and Depth
- **Elevation 1**: `0 2px 4px rgba(0,0,0,0.3)` - Subtle depth
- **Elevation 2**: `0 4px 8px rgba(0,0,0,0.4)` - Medium depth
- **Elevation 3**: `0 8px 16px rgba(0,0,0,0.5)` - High depth

### Border Styles
- **Technical**: 2px solid with slight glow effect
- **Rounded**: 4px border radius for modern tech feel
- **Sharp**: 0px border radius for industrial/military precision

## Component Styling

### Buttons
- **Primary**: Mars orange background with white text
- **Secondary**: Dark background with orange border
- **Success**: Green background for positive actions
- **Warning**: Yellow background for caution
- **Danger**: Red background for critical actions

### Status Indicators
- **Active**: Pulsing green glow
- **Inactive**: Dimmed gray
- **Warning**: Pulsing yellow
- **Error**: Pulsing red
- **Moving**: Animated orange glow

### Panels and Containers
- **Main**: Dark space black with subtle orange borders
- **Secondary**: Slightly lighter dark with blue accents
- **Highlight**: Orange-tinted backgrounds for active areas

## Animation Principles

### Timing
- **Fast**: 0.15s - Quick feedback
- **Medium**: 0.3s - Standard transitions
- **Slow**: 0.6s - Dramatic state changes

### Easing
- **Technical**: `ease-in-out` - Mechanical precision
- **Organic**: `cubic-bezier(0.4, 0, 0.2, 1)` - Natural movement
- **Bounce**: `cubic-bezier(0.68, -0.55, 0.265, 1.55)` - Playful interaction

### Effects
- **Glow**: Subtle outer glow for active elements
- **Pulse**: Rhythmic opacity changes for status indicators
- **Slide**: Smooth horizontal movement for gate animations
- **Particle**: Small glowing dots for dynamic effects

## Mars Exploration Theme Elements

### Iconography
- Rovers with tracks/wheels
- Communication antennas
- Solar panels
- Robotic arms
- Sensor arrays
- Geometric patterns inspired by spacecraft

### Environmental
- Dusty, rocky terrain textures
- Layered mountain silhouettes
- Atmospheric haze effects
- Grid patterns suggesting navigation systems
- Technical readouts and data overlays

## Implementation Notes

### Accessibility
- Maintain 4.5:1 contrast ratio minimum
- Ensure color is not the only indicator of state
- Provide text alternatives for visual elements
- Support keyboard navigation

### Responsive Design
- Scale elements proportionally
- Maintain readability at all sizes
- Adapt layouts for different screen orientations
- Preserve visual hierarchy

### Performance
- Use CSS transforms for animations
- Minimize repaints and reflows
- Optimize image assets
- Consider reduced motion preferences 