import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { d3ChartDefaults } from './config';

interface VolumeData {
  timestamp: number;
  volume: number;
  type: 'buy' | 'sell';
}

interface VolumeChartProps {
  data: VolumeData[];
  width?: number;
  height?: number;
}

export function VolumeChart({ data, width = 800, height = 400 }: VolumeChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.length) return;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();

    const { margin } = d3ChartDefaults;
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales
    const xScale = d3.scaleTime()
      .domain(d3.extent(data, d => new Date(d.timestamp)) as [Date, Date])
      .range([0, innerWidth]);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.volume) || 0])
      .range([innerHeight, 0]);

    // Create axes
    const xAxis = d3.axisBottom(xScale)
      .ticks(5)
      .tickFormat(d3.timeFormat('%H:%M') as any);

    const yAxis = d3.axisLeft(yScale)
      .tickFormat(d => `${d3.format(',.0f')(d as number)}`);

    svg.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis);

    svg.append('g')
      .call(yAxis);

    // Add labels
    svg.append('text')
      .attr('x', innerWidth / 2)
      .attr('y', innerHeight + margin.bottom - 5)
      .style('text-anchor', 'middle')
      .text('Time');

    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerHeight / 2)
      .attr('y', -margin.left + 15)
      .style('text-anchor', 'middle')
      .text('Volume');

    // Create volume bars
    const barWidth = innerWidth / data.length;

    const bars = svg.selectAll('rect')
      .data(data)
      .enter()
      .append('rect')
      .attr('x', (d, i) => i * barWidth)
      .attr('y', d => yScale(d.volume))
      .attr('width', barWidth - 1)
      .attr('height', d => innerHeight - yScale(d.volume))
      .attr('fill', d => d3ChartDefaults.colors[d.type])
      .attr('opacity', 0.7)
      .style('transition', `all ${d3ChartDefaults.animation.duration}ms ease`);

    // Add tooltips
    const tooltip = d3.select('body')
      .append('div')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', d3ChartDefaults.tooltip.backgroundColor)
      .style('border', `${d3ChartDefaults.tooltip.borderWidth}px solid ${d3ChartDefaults.tooltip.borderColor}`)
      .style('border-radius', `${d3ChartDefaults.tooltip.borderRadius}px`)
      .style('padding', `${d3ChartDefaults.tooltip.padding}px`)
      .style('font-size', `${d3ChartDefaults.tooltip.fontSize}px`);

    bars.on('mouseover', (event, d) => {
      tooltip
        .style('visibility', 'visible')
        .html(`
          <div>
            <strong>Volume:</strong> ${d.volume.toLocaleString()}<br/>
            <strong>Type:</strong> ${d.type.toUpperCase()}<br/>
            <strong>Time:</strong> ${new Date(d.timestamp).toLocaleTimeString()}
          </div>
        `);
    })
    .on('mousemove', (event) => {
      tooltip
        .style('top', (event.pageY - 10) + 'px')
        .style('left', (event.pageX + 10) + 'px');
    })
    .on('mouseout', () => {
      tooltip.style('visibility', 'hidden');
    });

    // Add volume line
    const line = d3.line<VolumeData>()
      .x((d, i) => i * barWidth + barWidth / 2)
      .y(d => yScale(d.volume))
      .curve(d3.curveMonotoneX);

    svg.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', d3ChartDefaults.colors.default)
      .attr('stroke-width', 2)
      .attr('d', line);

    // Cleanup function
    return () => {
      tooltip.remove();
    };

  }, [data, width, height]);

  return <svg ref={svgRef} />;
} 