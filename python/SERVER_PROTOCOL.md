#Server Protocol Specification

##Message Structure
Each message is wrapped in an envelope which specifies the type of message and which displays it is intended for.

**Example:**
```json
{"type": "data", "displays": [0, 2], "message": {...}}
```

The `message` parameter contains the actual message.

**Available message types:**

* `data`: Send data to be displayed
* `control`: Set matrix options

##Message Types
In this section, we'll have a look at the different message types. In the JSON examples, only the `message` parameter will be shown.

###Data message
This message type is used to send display data to the display. It has several subtypes which specify what kind of data will be sent.

**Available subtypes:**

* `bitmap`: Send raw pixel data.
* `text`: Send text data.
* `sequence`: Send multiple messages to be displayed sequentially.

####Bitmap message
This subtype of message is used to send raw pixel data to the display.

**Parameters:**

* `align`: How to align the bitmap on the display. Can be `left`, `center` or `right`. If omitted or set to `null`, it defaults to left align, however it leaves the bitmap in its full size. If an alignment is specified, the bitmap will be cropped to fit the display if necessary. For scrolling text, `align` should always be omitted, for obvious reasons.
* `bitmap`: The bitmap data as a simple list of lists representing the rows of the display.
Each pixel is represented by either a `0` or a `1` for off and on states respectively.
* `blend_bitmap`: If this is set to `true`, the bitmap will be blended with whatever is already on the display. Defaults to `false`.
* `config`: A set of configuration options (see below) that will be applied to the message.

**Example:**
```json
{"align": "center", "blend_bitmap": false, "bitmap": [[1, 0, 0, 0, ...], [0, 1, 1, 0, ...], ...]}
```

####Text Messages
Text messages specify a text and various parameters to control how the text should look.

**Parameters:**

* `align`: How to align the text on the display. Can be `left`, `center` or `right`. If omitted or set to `null`, it defaults to left align, however it leaves the bitmap in its full size. If an alignment is specified, the bitmap will be cropped to fit the display if necessary. For scrolling text, `align` should always be omitted, for obvious reasons.
* `font`: The font to use for the text. The name of the font is sufficient here, the correct file path will be picked automatically. Defaults to `Arial` if omitted.
* `size`: The font size (in pixels) to use for the text. Defaults to `11` if omitted.
* `text`: The text to display.
* `parse_time_string`: If this is set to `true`, the text will be treated as a time format string (things like `%H:%M` will become `13:37`) *and keep the current time without the need for resending the message*. Defaults to `false`.
* `blend_bitmap`: If this is set to `true`, the text will be blended with whatever is already on the display. Defaults to `false`.
* `config`: A set of configuration options (see below) that will be applied to the message.

**Example:**
```json
{"align": "center", "font": "Arial", "size": 11, "parse_time_string": true, "blend_bitmap": false, "text": "Current Time: %H:%M", "config": {"display_mode": "scroll"}}
```

####Sequence Messages
This message subtype acts as an envelope for sending multiple messages to be displayed sequentially.
The message data consists of a list of whole messages, although the message envelopes in the list don't have the `displays`
parameter set. Also, nesting sequence messages is obviously not possible.

**Example:**
```json
{"type": "sequence", "data": [{"type": "bitmap", "data": {...}}, {"type": "text", "data": {...}}]}
```

###Control Messages
Control messages are used to set options in the matrix controller.

**Available options:**

Option|Choices
------|-------
`display_mode`|`static`, `scroll`
`scroll_speed`|Value from `1` to `255`
`scroll_direction`|`left`, `right`
`scroll_mode`|`repeat-on-end`, `repeat-on-disappearance`, `repeat-after-gap`
`scroll_gap`|Value from `0` to the number of installed matrix modules
`power_state`|`on`, `off`
`blink_frequency`|Value from `0` to `255`
`stop_indicator`|`on`, `off`

**Example:**
```json
{"scroll_direction": "right"}
```

##Examples of complete messages
Set displays 0 and 1 to display right-scrolling text:
```json
{
	"type": "control",
	"displays": [0, 1],
	"message": {
		"display_mode": "scroll",
		"scroll_direction": "right"
	}
}
```

Send the text "Welcome" in Arial Bold to display 3:
```json
{
	"type": "data",
	"displays": [3],
	"message": {
		"type": "text",
		"data": {
			"align": "center",
			"font": "Arial Bold",
			"size": 11,
			"text": "Welcome"
		}
	}
}
```

Send a sequence of a bitmap and a text with an inline image to display 2 where the bitmap and the text will be displayed for 5 seconds and 3.5 seconds respectively:
```json
{
	"type": "data",
	"displays": [2],
	"message": {
		"type": "sequence",
		"data": [
			{
				"type": "bitmap",
				"data": {
					"duration": 5.0,
					"align": "right",
					"bitmap": [
						[0, 1, 0, 1, 1, 1, 0, 1, ...],
						[1, 1, 1, 0, 1, 1, 0, 0, ...],
						...
					]
				}
			},
			{
				"type": "text",
				"data": {
					"duration": 3.5,
					"align": null,
					"font": "FreeSans",
					"size": 11,
					"text": "@img:<sun.png> What a nice day!"
				}
			}
		]
	}
}
```

Set a text on display 0 that looks like a line number and destination on a train by blending two messages together:
```json
{
	"type": "data",
	"displays": [0],
	"message": {
		"type": "text",
		"data": {
			"align": "left",
			"font": "Arial Bold",
			"size": 11,
			"text": "U5"
		}
	}
}
```
```json
{
	"type": "data",
	"displays": [0],
	"message": {
		"type": "text",
		"data": {
			"align": "center",
			"font": "Arial",
			"size": 11,
			"blend_bitmap": true,
			"text": "Hauptbahnhof"
		}
	}
}
```