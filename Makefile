.PHONY: up down build logs test clean

## Sobe todos os serviços (build se necessário)
up:
	docker compose up --build

## Sobe em background
up-d:
	docker compose up --build -d

## Para e remove containers
down:
	docker compose down

## Rebuild forçado
build:
	docker compose build --no-cache

## Logs em tempo real
logs:
	docker compose logs -f

## Testa endpoints principais via curl
test:
	@echo "=== Health do Gateway ==="
	curl -s http://localhost:8080/health | python -m json.tool
	@echo "\n=== Recomendações (student_id=1) ==="
	curl -s "http://localhost:8080/recommendations?student_id=1" | python -m json.tool
	@echo "\n=== Conteúdos de Matemática ==="
	curl -s "http://localhost:8080/content?topic=matematica" | python -m json.tool
	@echo "\n=== Estado do Circuit Breaker ==="
	curl -s http://localhost:8080/circuit-breaker/status | python -m json.tool

## Remove containers, volumes e imagens do projeto
clean:
	docker compose down -v --rmi local
