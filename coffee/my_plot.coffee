import * as p from "core/properties"

import {PlotView, Plot} from "models/plots/plot"
import {Signal} from "core/signaling"

export class MyPlotView extends PlotView
    className: "MyPlotView"

    initialize: (options) ->
        super(options)
        @add_callbacks()

    render: () ->
        super()
        @add_callbacks()

    add_callbacks: () ->
        @el.ondragover = (ev) => @allow_drop ev
        @el.ondrop = (ev) => @drop ev
        return @

    allow_drop: (ev) ->
        ev.preventDefault()

    drop: (ev) ->
        ev.preventDefault()
        @model.document.event_manager.send_event({
            "event_name": "add_line", 
            "event_values" : {
                "model_id": @model.ref().id,
                "data": ev.dataTransfer.getData("text")}})

export class MyPlot extends Plot
    type: 'MyPlot'
    default_view: MyPlotView
