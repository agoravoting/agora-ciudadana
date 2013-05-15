(function() {
    var Charts = this.Charts = {};
    Charts.grad = Math.PI/180;

    Charts.arc = function(data,
                          node,
                          selector,
                          key_selector,
                          color,
                          width,
                          height) {
        var radius = Math.min(width, height);

        var pie = d3.layout.pie()
            .sort(null)
            .value(function(d) { return selector(d) })
            .startAngle(-90*Charts.grad).endAngle(90*Charts.grad);

        var arc = d3.svg.arc()
            .innerRadius(radius - 150)
            .outerRadius(radius - 40);

        var arc2 = d3.svg.arc()
            .innerRadius(radius - 150)
            .outerRadius(radius - 5);

        var svg = d3.select(node).append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(" + width / 2 + "," + height + ")");

        function sweep(a) {
            var i = d3.interpolate({startAngle: -90*Charts.grad, endAngle: -90*Charts.grad}, a);
            return function(t) {
                return arc(i(t));
            };
        }

        var g = svg.selectAll(".arc")
                   .data(pie(data))
                   .enter()
                   .append("g")
                   .attr("class", "arc");

        g.append("path")
         .attr("d", arc)
         .attr("fill", function(d, i) { return color(i); })
         .transition()
         .duration(2000)
         .each("end", function(d, i) {
            d3.select(this)
             .on('mouseover', Charts._arc_mouseover(this, arc2, key_selector))
             .on('mouseout', Charts._arc_mouseout(this, arc));
         })
         .attrTween("d", sweep);
    },

    Charts._arc_mouseover = function(o, arc2, key_selector) {
        var obj = d3.select(o);
        var key = key_selector(obj.data()[0].data);
        var val = obj.data()[0].value;
        var svg = d3.select('svg');
        var width = svg.attr("width");
        var height = svg.attr("height");
        return function () {
            obj.transition()
            .attr("d", arc2)
            .duration(200);

            d3.select("g").append("text")
                .attr("class", "textg")
                .attr("dy", "-4em")
                .attr("text-anchor", "middle")
                .style("font", "300 24px Sans Serif") 
                .text(key);

            d3.select("g").append("text")
                .attr("class", "textg")
                .attr("dy", "-1em")
                .attr("text-anchor", "middle")
                .style("font", "700 24px Sans Serif") 
                .text(val);
        }
    }

    Charts._arc_mouseout = function(o, arc) {
        var obj = d3.select(o);
        return function() {
            obj.transition()
            .attr("d", arc)
            .duration(500);
            d3.selectAll(".textg").remove();
        }
     }
}).call(this);
