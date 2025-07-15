eval $(minikube docker-env)

cd image
docker build -t teastore/image .
cd ..

cd inventory
docker build -t teastore/inventory .
cd ..

cd order
docker build -t teastore/order .
cd ..

cd product
docker build -t teastore/product .
cd ..

cd recommender
docker build -t teastore/recommender .
cd ..

cd recommender_starter
docker build -t teastore/recommender-starter .
cd ..

cd temporal-worker
docker build -t teastore/temporal-worker .
cd ..

cd temporal-core
docker build -t teastore/temporal-core .
cd ..

cd user
docker build -t teastore/user .
cd ..

cd webui
docker build -t teastore/webui .
cd ..