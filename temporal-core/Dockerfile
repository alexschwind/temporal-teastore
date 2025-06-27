FROM alpine
WORKDIR /app
COPY ./temporal /app/temporal
CMD ["./temporal", "server", "start-dev", "--db-filename", "temporal-db.db", "--ui-ip", "0.0.0.0", "--ip", "0.0.0.0"]