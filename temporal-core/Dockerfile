FROM alpine
WORKDIR /app
COPY ./temporal /app/temporal
RUN chmod +x /app/temporal
CMD ["/app/temporal", "server", "start-dev", "--ui-ip", "0.0.0.0", "--ip", "0.0.0.0", "--log-config", "--log-level", "debug"]