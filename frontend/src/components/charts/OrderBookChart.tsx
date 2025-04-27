import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { d3ChartDefaults } from './config';

interface OrderBookData {
  price: number;
  amount: number;
  type: 'bid' | 'ask';
}

interface OrderBookChartProps {
  data: OrderBookData[];
  width?: number;
  height?: number;
}

export function OrderBookChart({ data, width = 800, height = 400 }: OrderBookChartProps) {
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
    const xScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.amount) || 0])
      .range([0, innerWidth]);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.price) || 0])
      .range([innerHeight, 0]);

    // Create axes
    const xAxis = d3.axisBottom(xScale)
      .ticks(5)
      .tickFormat(d => d3.format('.2f')(d as number));

    const yAxis = d3.axisLeft(yScale)
      .tickFormat(d => `$${d3.format(',.0f')(d as number)}`);

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
      .text('Amount');

    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerHeight / 2)
      .attr('y', -margin.left + 15)
      .style('text-anchor', 'middle')
      .text('Price');

    // Create bars
    const barWidth = innerWidth / data.length;

    const bars = svg.selectAll('rect')
      .data(data)
      .enter()
      .append('rect')
      .attr('x', (d, i) => i * barWidth)
      .attr('y', d => yScale(d.price))
      .attr('width', barWidth - 1)
      .attr('height', d => innerHeight - yScale(d.price))
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
            <strong>Price:</strong> $${d.price.toLocaleString()}<br/>
            <strong>Amount:</strong> ${d.amount.toFixed(4)}<br/>
            <strong>Type:</strong> ${d.type.toUpperCase()}
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

    // Cleanup function
    return () => {
      tooltip.remove();
    };

  }, [data, width, height]);

  return <svg ref={svgRef} />;
} 