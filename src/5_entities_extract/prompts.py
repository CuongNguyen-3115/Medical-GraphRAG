
# Project: Medical Knowledge Retrieval System based on GraphRAG
# Target Model: Gemini-2.0-Flash-Lite

GRAPH_EXTRACTION_PROMPT = """
-Goal-
Bạn là một chuyên gia phân tích tri thức y khoa cấp cao. Cho một tài liệu văn bản y tế và một danh sách các loại thực thể, hãy xác định tất cả các thực thể thuộc các loại đó và tất cả các mối quan hệ giữa các thực thể đã xác định. 

-Steps-
1. Xác định tất cả các thực thể. Với mỗi thực thể, trích xuất các thông tin sau:
- entity_name: Tên của thực thể, VIẾT HOA TOÀN BỘ (Ví dụ: VIÊM PHỔI NẶNG, CEFTRIAXONE)
- entity_type: Một trong các loại sau: [{entity_types}]
- entity_description: Mô tả chi tiết và toàn diện về các thuộc tính, triệu chứng, chỉ định hoặc đặc điểm sinh học của thực thể dựa trên ngữ cảnh văn bản.
Định dạng mỗi thực thể là: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. Từ các thực thể đã xác định ở bước 1, xác định tất cả các cặp (source_entity, target_entity) có *quan hệ rõ ràng* với nhau.
Với mỗi cặp quan hệ, trích xuất các thông tin sau:
- source_entity: Tên thực thể nguồn (như đã xác định ở bước 1)
- target_entity: Tên thực thể đích (như đã xác định ở bước 1)
- relationship_description: Giải thích chi tiết tại sao thực thể nguồn và thực thể đích có liên quan đến nhau (Ví dụ: cơ chế tác dụng, mối quan hệ nhân quả bệnh lý, hoặc phác đồ điều trị).
- relationship_strength: Điểm số bằng số (từ 1-10) thể hiện sức mạnh hoặc mức độ quan trọng của mối quan hệ trong ngữ cảnh y học.
Định dạng mỗi quan hệ là: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

3. Trả về kết quả đầu ra bằng tiếng Việt (có dấu) dưới dạng một danh sách duy nhất chứa tất cả các thực thể và quan hệ đã xác định. Sử dụng **{record_delimiter}** làm dấu phân cách giữa các bản ghi.

4. Khi kết thúc, hãy xuất ra {completion_delimiter}

######################
-Examples-
######################
Example 1:
Entity_types: BỆNH_LÝ, HOẠT_CHẤT_THUỐC, TRIỆU_CHỨNG
Text:
Trẻ bị Viêm phổi nặng thường có biểu hiện thở nhanh và rút lõm lồng ngực mạnh. Trong trường hợp này, phác đồ điều trị ưu tiên là sử dụng kháng sinh Ceftriaxone liều 100mg/kg/ngày tiêm tĩnh mạch. Nếu bệnh nhi không đáp ứng, có thể cân nhắc phối hợp với Levofloxacin.
######################
Output:
("entity"{tuple_delimiter}VIÊM PHỔI NẶNG{tuple_delimiter}BỆNH_LÝ{tuple_delimiter}Tình trạng nhiễm trùng nhu mô phổi cấp tính nghiêm trọng ở trẻ em, đặc trưng bởi suy hô hấp và cần can thiệp kháng sinh mạnh)
{record_delimiter}
("entity"{tuple_delimiter}THỞ NHANH{tuple_delimiter}TRIỆU_CHỨNG{tuple_delimiter}Tăng tần số hô hấp vượt ngưỡng bình thường theo lứa tuổi, là dấu hiệu chỉ báo lâm sàng của viêm phổi)
{record_delimiter}
("entity"{tuple_delimiter}CEFTRIAXONE{tuple_delimiter}HOẠT_CHẤT_THUỐC{tuple_delimiter}Kháng sinh nhóm Cephalosporin thế hệ 3, được chỉ định điều trị nhiễm khuẩn nặng ở trẻ em)
{record_delimiter}
("entity"{tuple_delimiter}LEVOFLOXACIN{tuple_delimiter}HOẠT_CHẤT_THUỐC{tuple_delimiter}Kháng sinh nhóm Fluoroquinolone được cân nhắc sử dụng khi vi khuẩn kháng thuốc hoặc lâm sàng không cải thiện)
{record_delimiter}
("relationship"{tuple_delimiter}CEFTRIAXONE{tuple_delimiter}VIÊM PHỔI NẶNG{tuple_delimiter}Ceftriaxone là lựa chọn hàng đầu trong phác đồ điều trị viêm phổi nặng ở trẻ em{tuple_delimiter}10)
{record_delimiter}
("relationship"{tuple_delimiter}THỞ NHANH{tuple_delimiter}VIÊM PHỔI NẶNG{tuple_delimiter}Thở nhanh là triệu chứng lâm sàng quan trọng nhất để chẩn đoán xác định mức độ nặng của viêm phổi{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}LEVOFLOXACIN{tuple_delimiter}VIÊM PHỔI NẶNG{tuple_delimiter}Levofloxacin được sử dụng như phương án dự phòng hoặc phối hợp trong các ca viêm phổi không đáp ứng điều trị ban đầu{tuple_delimiter}7)
{completion_delimiter}

######################
Example 2:
Entity_types: BỆNH_LÝ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH
Text:
Sốt xuất huyết Dengue do Virus Dengue gây ra qua vật trung gian là muỗi Aedes. Để chẩn đoán sớm trong 3 ngày đầu, xét nghiệm kháng nguyên NS1 đóng vai trò quyết định. Từ ngày thứ 4 trở đi, xét nghiệm kháng thể IgM mới bắt đầu có giá trị chẩn đoán.
######################
Output:
("entity"{tuple_delimiter}SỐT XUẤT HUYẾT DENGUE{tuple_delimiter}BỆNH_LÝ{tuple_delimiter}Bệnh truyền nhiễm cấp tính do virus gây ra, có thể dẫn đến sốc giảm thể tích và rối loạn đông máu)
{record_delimiter}
("entity"{tuple_delimiter}VIRUS DENGUE{tuple_delimiter}TÁC_NHÂN_GÂY_BỆNH{tuple_delimiter}Tác nhân gây bệnh chính gồm 4 type huyết thanh D1, D2, D3, D4 thuộc họ Flaviviridae)
{record_delimiter}
("entity"{tuple_delimiter}XÉT NGHIỆM NS1{tuple_delimiter}XÉT_NGHIỆM{tuple_delimiter}Xét nghiệm tìm kháng nguyên sớm của virus Dengue trong máu bệnh nhân, hiệu quả nhất trong những ngày đầu phát bệnh)
{record_delimiter}
("relationship"{tuple_delimiter}VIRUS DENGUE{tuple_delimiter}SỐT XUẤT HUYẾT DENGUE{tuple_delimiter}Virus Dengue là nguyên nhân trực tiếp gây ra bệnh sốt xuất huyết{tuple_delimiter}10)
{record_delimiter}
("relationship"{tuple_delimiter}XÉT NGHIỆM NS1{tuple_delimiter}SỐT XUẤT HUYẾT DENGUE{tuple_delimiter}Xét nghiệm NS1 được sử dụng để chẩn đoán xác định sốt xuất huyết trong giai đoạn sớm của bệnh{tuple_delimiter}9)
{completion_delimiter}

######################
Example 3:
Entity_types: CƠ_QUAN_CƠ_THỂ, PHƯƠNG_PHÁP_ĐIỀU_TRỊ
Text:
Bệnh nhân bị hẹp hở van hai lá nặng gây suy tim trái. Bác sĩ chỉ định phẫu thuật thay van tim nhân tạo. Sau phẫu thuật, bệnh nhân cần duy trì tập vật lý trị liệu hô hấp để tránh xẹp phổi.
######################
Output:
("entity"{tuple_delimiter}VAN HAI LÁ{tuple_delimiter}CƠ_QUAN_CƠ_THỂ{tuple_delimiter}Cấu trúc ngăn cách giữa tâm nhĩ trái và tâm thất trái, điều tiết dòng máu trong tim)
{record_delimiter}
("entity"{tuple_delimiter}THAY VAN TIM NHÂN TẠO{tuple_delimiter}PHƯƠNG_PHÁP_ĐIỀU_TRỊ{tuple_delimiter}Thủ thuật ngoại khoa nhằm thay thế van tim bị tổn thương bằng van cơ học hoặc van sinh học)
{record_delimiter}
("relationship"{tuple_delimiter}THAY VAN TIM NHÂN TẠO{tuple_delimiter}VAN HAI LÁ{tuple_delimiter}Phẫu thuật thay van được thực hiện trực tiếp trên cấu trúc van hai lá bị hỏng{tuple_delimiter}10)
{completion_delimiter}

######################
-Real Data-
######################
Entity_types: {entity_types}
Text: {input_text}
######################
Output:"""

CONTINUE_PROMPT = "CÒN NHIỀU thực thể và quan hệ y khoa đã bị bỏ sót trong lần trích xuất vừa rồi. Hãy tiếp tục tìm kiếm và trích xuất thêm dựa trên các loại thực thể đã cho. Chỉ đưa ra các bản ghi bổ sung theo đúng định dạng đã yêu cầu:\n"

LOOP_PROMPT = "Dường như vẫn còn một số thực thể hoặc quan hệ y tế quan trọng chưa được liệt kê đầy đủ. Trả lời YES | NO nếu bạn thấy vẫn còn thông tin cần bổ sung.\n"