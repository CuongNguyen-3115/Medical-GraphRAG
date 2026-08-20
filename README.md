# Medical GraphRAG: Hệ thống tra cứu tri thức y khoa dựa trên Kiến thức đồ thị

Dự án nghiên cứu và xây dựng hệ thống tra cứu thông tin y khoa thông minh, kết hợp giữa mô hình ngôn ngữ lớn (LLM) và cơ sở dữ liệu đồ thị (Knowledge Graph). Hệ thống tập trung vào việc cung cấp các thông tin chẩn đoán chính xác, có nguồn gốc rõ ràng từ các cổng thông tin y tế chính thống tại Việt Nam.

## Các thành phần cốt lõi

### 1. Thu thập dữ liệu y khoa (Medical Data Crawling)
* Tự động hóa quy trình thu thập dữ liệu về hướng dẫn chẩn đoán và điều trị từ Cục Quản lý Khám, chữa bệnh (kcb.vn).
* Xử lý và chuẩn hóa các nguồn dữ liệu phi cấu trúc (PDF, văn bản thô) sang định dạng Markdown để chuẩn bị cho các bước xử lý tiếp theo.

### 2. Xây dựng Knowledge Graph sử dụng LLM
* Ứng dụng mô hình ngôn ngữ lớn (LLM) thông qua kỹ thuật Prompt Engineering để trích xuất các thực thể y tế (Bệnh, Triệu chứng, Thuốc, Quy trình) và các mối quan hệ giữa chúng.
* Lưu trữ và quản lý mạng lưới tri thức trên cơ sở dữ liệu đồ thị Neo4j, cho phép truy vấn các mối quan hệ đa tầng phức tạp.

### 3. Cơ chế Hybrid RAG và Điều hướng (Query Routing)
* Kết hợp giữa Retrieval-Augmented Generation (RAG) truyền thống dựa trên Vector Database và truy xuất dựa trên đồ thị (Graph-based Retrieval).
* Xây dựng bộ điều hướng (Router) để phân tích ý định người dùng, từ đó quyết định lấy dữ liệu từ Graph, Vector DB hoặc kết hợp cả hai để đưa ra câu trả lời tối ưu nhất.

## Công nghệ sử dụng

* Ngôn ngữ lập trình: Python
* LLM: llama-3.3-70b-versatile / llama-3.1-8b-instant / Gemini 2.5 Flash
* Cơ sở dữ liệu đồ thị: Neo4j
* Cơ sở dữ liệu Vector: ChromaDB
* Framework: LangChain, LlamaIndex, Pydantic
* Thư viện xử lý dữ liệu: Pandas, PyMuPDF, BeautifulSoup4

## Lộ trình phát triển

- Đã hoàn thành: Thu thập dữ liệu từ kcb.vn và xử lý văn bản thô.
- Đã hoàn thành: Thiết kế Schema cho Knowledge Graph.
- Đang thực hiện: Pipeline trích xuất thực thể/quan hệ bằng LLM (Few-shot exemplars).
- Sắp tới: Xây dựng cơ chế Query Routing và đánh giá hệ thống (RAG Evaluation).

## Lưu ý

Dự án này được thực hiện phục vụ mục đích nghiên cứu học thuật trong khuôn khổ Đồ án tốt nghiệp. Các thông tin cung cấp từ hệ thống chỉ mang tính chất tham khảo, không thay thế cho các chỉ định y khoa chuyên môn.

An intelligent medical knowledge retrieval system using GraphRAG architecture, combining LLMs, Neo4j, and ChromaDB to provide accurate medical insights from kcb.vn.