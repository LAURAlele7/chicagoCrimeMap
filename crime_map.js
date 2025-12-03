// ---------- New D3 Abstract Crime Map ----------
async function createD3CrimeMap(mapData, geojsonData) {

    // 1. Parse month list
    const months = Object.keys(mapData.monthly_data).sort();
    const monthSelector = document.getElementById("monthSelector");

    // Fill dropdown
    months.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        monthSelector.appendChild(opt);
    });

    // Default month
    let currentMonth = months[0];

    // ----- Prepare SVG -----
    const width = 600;
    const height = 600;

    const container = d3.select("#map-chart");
    container.selectAll("*").remove(); // Clear previous

    const svg = container.append("svg")
        .attr("width", width)
        .attr("height", height)
        .style("background", "white")
        .style("border-radius", "8px")
        .style("box-shadow", "0 2px 4px rgba(0,0,0,0.1)");

    // Abstract Projection
    const projection = d3.geoIdentity()
        .reflectY(true)
        .fitSize([width, height], geojsonData);

    const path = d3.geoPath(projection);

    // ---------- Color scale (using your HOT colorscale) ----------
    const colorScale = d3.scaleSequential(d3.interpolateOrRd);  
    // NOTE: OrRd colors look like Plotly Hot; replace if you provide your own palette.

    // Tooltip
    const tooltip = d3.select("body")
      .append("div")
      .style("position", "absolute")
      .style("padding", "6px 10px")
      .style("background", "white")
      .style("border", "1px solid #ccc")
      .style("border-radius", "5px")
      .style("pointer-events", "none")
      .style("opacity", 0);

    // Drawing function
    function updateMap(month) {
        currentMonth = month;
        const monthData = mapData.monthly_data[month];

        // Convert crimes to dictionary by district
        const crimeByDist = {};
        monthData.forEach(d => {
            crimeByDist[d.District] = d.total_crimes;
        });

        const values = Object.values(crimeByDist);
        const maxCrime = d3.max(values);

        colorScale.domain([0, maxCrime]);

        // Bind polygons
        svg.selectAll("path")
            .data(geojsonData.features)
            .join("path")
            .attr("d", d => path(d))
            .attr("stroke", "#333")
            .attr("stroke-width", 0.5)
            .attr("fill", d => {
                const dist = parseInt(d.properties.dist_num);
                const crime = crimeByDist[dist] || 0;
                return colorScale(crime);
            })
            .on("mouseover", function(event, d) {
                const dist = parseInt(d.properties.dist_num);
                const crime = crimeByDist[dist] || 0;
                tooltip.style("opacity", 1)
                    .html(
                        `<b>District ${dist}</b><br>` +
                        `Crimes: ${crime}<br>` +
                        `Month: ${currentMonth}`
                    );
                d3.select(this).attr("stroke-width", 2);
            })
            .on("mousemove", function(event) {
                tooltip
                  .style("left", (event.pageX + 10) + "px")
                  .style("top", (event.pageY - 20) + "px");
            })
            .on("mouseout", function() {
                tooltip.style("opacity", 0);
                d3.select(this).attr("stroke-width", 0.5);
            });
    }

    // Initial draw
    updateMap(currentMonth);

    // Month change listener
    monthSelector.addEventListener("change", (e) => {
        updateMap(e.target.value);
    });
}
