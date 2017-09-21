dbbk
====

A streaming visualization library written with bokeh.

Installation
------------

1. Get bokeh, pandas, flask, nodejs with your favourite package manager.
2. Clone this repo

Run
---

```
python bokeh_flask.py
```

A browser window will popup.

You can now send data opening a new window and typing

```
http://localhost:8080/add/experiment1/variable1/1/1
```
then
```
http://localhost:8080/add/experiment1/variable1/2/2
```

Click 'Add Plot' button.

Wait a couple of seconds and drag a table row to the plot.

![Screen shot][https://raw.githubusercontent.com/dmitriy-serdyuk/dbbk/master/screenshot.png]
