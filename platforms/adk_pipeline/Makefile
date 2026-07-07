.PHONY: build run dry web web-console start stop dashboard-daemon clean

build:
	go build -o pipeline .

run: build
	./pipeline console

dry: build
	echo "test content" | ./pipeline console

web: build
	./pipeline web --port 8080 api webui

web-console: build
	./pipeline web --port 8080 api

start: build
	bash start-web.sh

stop:
	bash stop-web.sh

dashboard: build
	cd dashboard && go build -o ../dashboard . && cd ..

dashboard-run: dashboard
	./dashboard

dashboard-daemon: dashboard
	@echo "Starting dashboard on port 8081..."
	@nohup ./dashboard > dashboard.log 2>&1 & echo $$! > dashboard.pid
	@sleep 1
	@echo "Dashboard started (PID $$(cat dashboard.pid)) at http://localhost:8081"

clean:
	rm -f pipeline dashboard pipeline.pid dashboard.pid
