/*
(c) 2015-2017 Tuomas Airaksinen

This file is part of automate-webui.

automate-webui is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

automate-webui is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with automate-webui.  If not, see <http://www.gnu.org/licenses/>.
*/

var socket = undefined;

var plot_data = {};
var plotters = {};

function get_data(data) {
    return [
        {
            data: data,
            lines: {show: true, steps: true, lineWidth: 0.7},
            color: "blue"
        }
    ]
}

function plot(object_name) {
    var targets = $(".graph-" + object_name);
    if(targets.length === 0 || plotters[object_name])
        return;

    plotters[object_name] = [];
    var initial_data = plot_data[object_name] || [];
    for (var i = 0; i < targets.length; i++) {
        var plot = $.plot(targets[i],
            get_data(initial_data),
            {
                xaxis: {
                    mode: "time",
                    timeformat: "%H:%M",
                    timezone: "browser"
                },
                yaxis: {
                    zoomRange: [1, 1]
                },
                zoom: {
                    interactive: true
                },
                pan: {
                    interactive: true
                },
                grid: {
                    hoverable: true,
                    clickable: true
                },
                touch: {
                    scale: 'x',
                    pan: 'x'
                }

            }
        );
        plot.setupGrid();
        plot.draw();
        plotters[object_name].push(plot);
    }

    $.getJSON("/history.json/object/" + object_name, function(data_points) {
        plot_data[object_name] = data_points;
        $.each(plotters[object_name], function(i, plotter) {
            plotter.setData(get_data(data_points));
            plotter.setupGrid();
            plotter.draw();
        });
    });

    $("<div id='tooltip-" + object_name + "'></div>").css({
        position: "absolute",
        display: "none",
        border: "1px solid #fdd",
        padding: "2px",
        "background-color": "#fee",
        opacity: 0.80
    }).appendTo("body");

    targets.bind("plothover plotclick", function (event, pos, item) {
        if (item) {
            var t = new Date(item.datapoint[0]),
                y = item.datapoint[1].toFixed(2);

            $("#tooltip-" + object_name).html(t.getDate() + '.' + t.getMonth() +
                ' ' + t.getHours() + ':' + t.getMinutes() + ": <b>" + y+"</b>")
                .css({top: item.pageY+5, left: item.pageX+5})
                .fadeIn(200);
        } else {
            $("#tooltip-"+object_name).hide();
        }
    });
}

function object_status_changed(obj)
{
    var status = obj['status'];
    var display = obj['display'];
    var changing = obj['changing'];
    var name = obj['name'];
    var time = obj['time'];

    var status_str = display; //tString(status).capitalize();

    var status_element = $('.object_status_' + name);
    if (status) {
        status_element.removeClass('status_inactive');
        if (changing)
            status_element.addClass('status_changing');
        else {
            status_element.removeClass('status_changing');
            status_element.addClass('status_active');
        }
    }
    else {
        status_element.removeClass('status_active');
        if (changing)
            status_element.addClass('status_changing');
        else {
            status_element.removeClass('status_changing');
            status_element.addClass('status_inactive');
        }
    }

    status_element.html(status_str);
    $(':input[name="name"][value="' + name + '"]').parent().find('#id_status').val(status);
    var sliders = $('.slider_sensor_'+name);
    sliders.slider('setValue', status);
    var plotters_ = plotters[name];
    if(plotters_) {
        var data = plot_data[name];
        var prev_t = 0;

        if(data.length > 0)
            prev_t = data[data.length -1][0];

        data.push([time, status]);
        $.each(plotters_, function(i, plotter) {
            plotter.setData(get_data(data));
            plotter.setupGrid();
            plotter.draw();
            if (prev_t) {
                var xaxis = plotter.getXAxes()[0];
                var new_left = xaxis.min + (time - prev_t);
                plotter.pan({left: xaxis.p2c(new_left), top: 0})
            }
        });
    }
}

function update_actuator(obj)
{
    var name = obj['name'];
    var html = obj['html'].replace(/__SOURCE__/g, source);

    var elements = $('div.actuator_element_' + name);
    elements.html(html);
    refresh_queries();
}

function program_status_changed(obj)
{
    var name = obj['name'];
    status = obj['active'];
    var status_str = String(status).capitalize();

    var status_element = $('#program_active_' + name);
    if (status) {
        status_element.removeClass('status_inactive');
        status_element.addClass('status_active');
    }
    else {
        status_element.removeClass('status_active');
        status_element.addClass('status_inactive');
    }

    status_element.html(status_str);
}

function write_log(obj)
{
    pre = $('pre.small_log,pre.log');
    pre.append(obj.data);
    pre.scrollTop(pre.prop("scrollHeight"));
}

function get_websocket_url() {
    var loc = window.location, new_uri;
    if (loc.protocol === "https:") {
        new_uri = "wss:";
    } else {
        new_uri = "ws:";
    }
    new_uri += "//" + loc.host;
    new_uri += "/socket";
    return new_uri;
}


function refresh_queries() {
    var mysliders = $('input.sliderfields');
    mysliders.slider();

    if(socket) {
        $('a.mytoggle').click(function (ev) {
            ev.preventDefault();

            var new_status = !Boolean($.trim($(this).text()) == 'True');
            var data = {action: 'set_status', name: $(this).data('name'), status: new_status};
            var message = JSON.stringify(data);
            socket.send(message);
        });

        $(':submit[name="set_status"]').click(function (ev) {
            ev.preventDefault();
            var form = $(this).parents('form');
            var name = form.find('#id_name').attr('value');
            var status = form.find('#id_status').val();
            var data = {action: 'set_status', name: name, status: status};
            var message = JSON.stringify(data);
            socket.send(message);
        });

        $(':submit[name="run_cmd"]').click(function (ev) {
            ev.preventDefault();
            var form = $(this).parents('form');
            var cmd = form.find('#id_cmd');
            var data = {action: 'send_command', command: cmd.val()};
            var message = JSON.stringify(data);
            socket.send(message);
            cmd.val('');
        });

        mysliders.on('slideStop', function(ev) {
            var form = $(this).parents('form');
            var name = form.find('#id_name').attr('value');
            var status = ev.value;
            var data = {action: 'set_status', name: name, status: status};
            var message = JSON.stringify(data);
            socket.send(message);
        });
    }
    else {
         mysliders.on('slideStop', function(ev) {
             var form = $(this).parents('form');
             form.submit();
        });
    }

    $('.request_panel').click(function(ev) {
        if($(ev.target).hasClass('edit_area') || $(ev.target).parents().hasClass('edit_area'))
            return;

        //var pls_str = $(this).data('placeholder');
        var name = $(this).data('name');
        var target = $(this).data('target');
        var parent = $(this).parents('.object_row');
        var placeholder = parent.nextAll('.collapse-' + target + '-' + name);

        var url = $(this).data('url');

        if(placeholder.hasClass('in')) {
            placeholder.collapse('hide');
        }
        else
        {
            if(target==="info") {
                $.ajax({
                    type: 'GET',
                    url: url,
                    success: function (d) {
                        placeholder.html(d);
                        placeholder.collapse('show');
                    }
                });
            }
            else if(target==="graph")
            {
                plot(name);
                placeholder.collapse('show');
            }
        }
    });
}

$(document).ready(function() {
    pre = $('pre.small_log,pre.log');
    pre.scrollTop(pre.prop("scrollHeight"));

    String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
    };

    if(window.WebSocket && source != 'login') {
        socket = new WebSocket(get_websocket_url());
        socket.onmessage = function (evt) {
            var obj = $.parseJSON(evt.data);
            switch (obj['action']) {
                case 'object_status':
                    object_status_changed(obj);
                    break;
                case 'program_active':
                    program_status_changed(obj);
                    break;
                case 'log':
                    write_log(obj);
                    break;
                case 'update_actuator':
                    update_actuator(obj);
                    break;
            }
        };
        socket.onclose = function () {
            location.reload();
        };

        socket.onopen = function () {
            if ($('pre.log').length > 0)
                socket.send(JSON.stringify({action: 'request_log'}));

            var objs = $('div.object_row');
            var names = [];
            for (var i = 0; i < objs.length; i++) {
                var name = $(objs[i]).data('name');
                if (name && !(name in names))
                    names.push(name)
            }
            socket.send(JSON.stringify({'action': 'subscribe', 'objects': names}));
            setInterval(function() {
                socket.send(JSON.stringify({action: 'ping'}));
            }, 60000);
        };
    }
    refresh_queries();
});


