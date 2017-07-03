import * as p from "core/properties"

import {DataTable, DataTableView} from "models/widgets/data_table"


export class MyDataTableView extends DataTableView
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
        rows = @$el.find('.bk-slick-row')
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

            
export class MyDataTable extends DataTable
    type: "MyDataTable"
    default_view: MyDataTableView
