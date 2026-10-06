<h1>Masters Dissertation Project</h1>
<h3>The Cost and Value of Traceability in ML-powered Solar Energy System for Anomaly Detection</h3>
<h4>Stack:</h4>
<ul>
  <li>FastAPI/Python</li>
  <li>React/TypeScript/TailwindCSS</li>
  <li>PostgreSQL</li>
  <li>Redis/Celery</li>
  <li>Docker</li>
</ul>
<p>This project aimed at designing and building a full-stack system with the ability to reconstruct data trace at fine granularity.</p>
<p>The system ingests solar generation and weather data from a peer-reviewed open source national aggregate dataset found: generation: https://data.open-power-system-data.org/time_series/ weather: https://data.open-power-system-data.org/weather_data/</p>
<p>Each row is validated at ingestion and assigned a trace_id which follows it through the system allowing for per-stage reconstruction of its path.</p>
<br>
<p>A live replay can be found here: https://solar-anomaly-detector.co.uk</p>
<p>Either the full dataset or an anomaly-rich section can be replayed by selecting from the controls on the right. Pressing 'Start Replay' will replay the ingestion and highlight anomalies detected.</p>
<br>
<p>Two detection systems were implemented. A deterministic rule-engine with rules such as: if generation < 0 && is_daytime -> flag_anomaly. Additionally, a isolation forest model was created but only to serve as a workload.</p>
<p>Selecting a trace_id will show the journey of the datapoint through the system and what detection system caught it.</p>

