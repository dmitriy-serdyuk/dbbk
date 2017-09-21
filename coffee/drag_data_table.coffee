import * as p from "core/properties"

import {DataTable, DataTableView} from "models/widgets/tables/data_table"


export class DragDataTableView extends DataTableView
    initialize: (options) ->
        super(options)
        @render()
        @grid.onSort.subscribe (event, args) =>
            @add_callbacks()

    render: () ->
        super()
        @add_callbacks()

    updateGrid: () ->
        super()
        @add_callbacks()

    updateSelection: () ->
        super()
        @add_callbacks()

    add_callbacks: () ->
        rows = $(@el).find('.slick-row')
        for row, i in rows
            row.setAttribute("draggable", "true")
            do (i, row) =>
                item = @data.getItem(i)
                row.ondragstart = (ev) => @drag(ev, item)
            row.ondragover = (ev) => @allow_drop ev
            row.ondrop = (ev) => @drop ev
        return @

    drag: (ev, i) ->
        i = JSON.stringify(i)
        ev.dataTransfer.setData("text", i)

    allow_drop: (ev) ->
        ev.preventDefault()

    drop: (ev) ->
        ev.preventDefault()

            
export class DragDataTable extends DataTable
    type: "DragDataTable"
    default_view: DragDataTableView
