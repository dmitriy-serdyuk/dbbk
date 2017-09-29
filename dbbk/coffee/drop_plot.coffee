import * as p from "core/properties"

import {PlotView, Plot} from "models/plots/plot"
import {Signal} from "core/signaling"

export class DropPlotView extends PlotView
    className: "DropPlotView"

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
        @render()
        ev.preventDefault()
        model_id = @model.ref().id
        for doc in Bokeh.documents
          if doc.get_model_by_id(model_id)
            @model.document.event_manager.send_event({
                "event_name": "add_line",
                "event_values" : {
                    "model_id": model_id,
                    "data": ev.dataTransfer.getData("text")}})

export class DropPlot extends Plot
    type: 'DropPlot'
    default_view: DropPlotView
