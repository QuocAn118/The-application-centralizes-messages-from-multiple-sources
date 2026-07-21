[https://github.com/QuocAn118/The-application-centralizes-messages-from-multiple-sources.git](https://github.com/QuocAn118/The-application-centralizes-messages-from-multiple-sources.git)

Nowadays, as businesses expand their operations and raise the quality of customer service, interactions increasingly take place on social media platforms. Customer support and consultation are commonly handled through chat channels associated with business accounts, such as Zalo OA, Facebook Fanpage, etc. in Vietnam. However, for businesses using multiple OA-based chat channels, managing various platforms and customer information simultaneously becomes difficult. Furthermore, the native features of OA do not fully meet the scalability and service-quality requirements of modern enterprises. For instance, OA currently supports only basic message sending and receiving, and lacks essential capabilities such as:  
Analyzing customer needs based on message content.  
Assigning tasks automatically according to staff specialization for specific products.  
Providing a system for managing employee KPIs and defining clear work shifts.  
Aggregating and reporting customer demand for products.  
Restricting access to customer message data, as all staff operate through a single shared OA account.  
Solution:  
From this, our team proposes a system capable of addressing all the issues mentioned above, named OmniChat.  
OmniChat is a system designed for the enterprise’s management and customer service departments across multiple social media platforms. The solution centralizes all messages from different channels into a single place while integrating business process management, providing a unified and efficient platform for the organization.  
The solution includes:  
Viewing and responding to customer messages from all platforms they use within a unified interface, with all actions performed through a single workflow.  
Providing message-content analysis capabilities, including keyword detection, to generate data that supports the enterprise’s internal operations and processes.  
Offering a comprehensive personnel management system, including working-time management, important-keyword management, and customer information management within the same application.  
Integrating automatic task assignment, enabling the enterprise to allocate tasks based on staff specialization according to customer message keywords, KPIs, and other operational criteria.  
Providing a comprehensive dashboard displaying key information such as daily message volume, customer consultation needs, and employee performance indicators including monthly targets.  
Function requirements:  
Key features:  
Enables receiving and responding to interactions from third-party platforms (such as Zalo OA) through API integration. Data exchange and communication with partner servers are automated in real time via a Webhook mechanism, ensuring synchronization and accuracy.  
Analyzes message content to identify keywords using the system’s algorithms, storing message data for the purpose of aggregating and reporting customer demand.  
Integrates personnel management features, including employee working-time tracking, KPI management, management of service-related important keywords and the enterprise’s specific operational requirements.  
Integrates automatic task assignment based on keyword-analysis algorithms that extract important keywords from customer messages to identify the appropriate department staff responsible for providing consultation. Task allocation is further optimized according to employee KPIs and real-time working status within each department.  
The system uses the data collected from integrated platforms to produce statistical reports that summarize customer interaction trends, message volume, and employee performance metrics within the enterprise’s specified reporting periods.  
OmniChat will support the following roles and their corresponding functionalities:  
Staff \- mobile app & web:  
Staff receives notifications for messages or consultation requests sent by customers through the enterprise’s OA account.  
Staff marks a request as “Completed” after providing support and consultation to the customer.  
Staff creates internal request forms such as leave requests, salary-increase requests, and other similar forms.  
Staff receives notifications when the request is approved or rejected by the Manager.  
Staff views basic customer information such as phone number, email, name, and other relevant details.  
Staff tracks their own basic information and personal performance data.  
Manager \- mobile app & web:  
Manager creates, updates, deletes, and monitors information of all Staff within their department.  
Manager creates, updates, deletes, and monitors KPI statistics of the department.  
Manager creates, updates, deletes, and monitors the list of keywords being used by the department.  
Manager reviews and approves or rejects all requests submitted by Staff in the department.  
Manager creates, updates, deletes, and monitors current shifts and the work schedule of employees.  
Manager assigns work shifts to employees.  
Admin \- mobile app & web:  
Admin views statistics by different data dimensions:  
By department  
By employee (Staff / Manager)  
By request type  
By time period  
Admin views the list of all keywords created by department Managers in the system.  
Admin manages the accounts of Staff and Managers.  
Admin assigns or switches permissions between Staff ↔ Manager.  
Nonfunctional requirements:  
Performance: The system must handle 1000 users simultaneously without performance issues.  
Security: The system must apply authentication and authorization mechanisms using JWT; encrypt sensitive data; protect the chat system’s communication channel with HTTPS/TLS; prevent common security vulnerabilities such as XSS and SQL Injection; and protect user data.  
Usability: The system must provide an intuitive and easy-to-use interface for both the Web App and Mobile App.  
Interoperability: The system must be tightly and seamlessly integrated with third-party APIs such as Zalo OA API, Meta Business Manager API, etc.  
Reliability: The system must ensure a minimum uptime of 99.5% with effective data backup and recovery mechanisms.

Students should apply a software development process following Agile Methodology or other suitable software development life cycle (SDLC) models, and use UML Specification 2.4 to describe requirement specification documents and design documents.  
a. Theory and practice (document):  
Students should apply knowledge from the courses SWD391, SWE102, SWR302, SWT301, and PMG201c, combined with advanced programming skills they get based on their curriculum or the OJT phase when implementing the capstone project.  
The system must be built using a 3-tier architecture (Client – Server – Database).  
Server-side technologies:  
\+ Language & Framework: PythonWeb API (high performance, rich ecosystem, cross-platform).  
\+ Database: PostgreSQL (Supabase).  
Client-side technologies:  
\+ Mobile App: React Native (good performance, flexible UI, shared codebase).  
\+ Web App: Next.js / React (modern, powerful framework for administrative dashboard systems).  
Third-party services:  
\+ Authentication: Custom system using Python Identity & JWT.  
\+ Deployment: Microsoft Azure or Google Cloud Platform.  
b. Products:  
The complete OmniChat system includes:  
Mobile application (React Native).  
Web application (ReactJS).  
Stable Backend system (Python).  
A comprehensive set of documentation, including:  
System Requirements Specification (SRS).  
System Design Document (SDD).  
Test Plan and Test Case Suite.  
Installation Guide.  
User Guide.  
c. Proposed Tasks:  
Task 1: Analyze and develop requirements; design UI/UX for website and mobile.  
Task 2: Develop the website using ReactJS and TypeScript.  
Task 3: Develop the mobile application using React Native.  
Task 4: Analyze and design the database along with the Microservices system.  
Task 5: Develop Backend APIs and Database using ASP.NET Core and PostgreSQL.  
Task 6: Integrate third-party APIs such as Zalo, Meta Business, etc.  
Task 7: Test performance using Unit, Integration, and System tests; deploy to cloud and CH Play.  
Task 8: Prepare and finalize all required project documentation.

Ngày nay, khi các doanh nghiệp mở rộng hoạt động và nâng cao chất lượng dịch vụ khách hàng, các tương tác ngày càng diễn ra trên các nền tảng mạng xã hội. Hỗ trợ khách hàng và tư vấn thường được thực hiện thông qua các kênh chat gắn với tài khoản doanh nghiệp, chẳng hạn như Zalo OA, Facebook Fanpage, v.v. tại Việt Nam. Tuy nhiên, đối với các doanh nghiệp sử dụng nhiều kênh chat dựa trên OA, việc quản lý đồng thời nhiều nền tảng và thông tin khách hàng trở nên khó khăn. Hơn nữa, các tính năng gốc của OA chưa đáp ứng đầy đủ yêu cầu về khả năng mở rộng và chất lượng dịch vụ của các doanh nghiệp hiện đại. Ví dụ, OA hiện chỉ hỗ trợ gửi và nhận tin nhắn cơ bản, và thiếu các khả năng thiết yếu như:

* Phân tích nhu cầu khách hàng dựa trên nội dung tin nhắn.  
* Tự động phân công công việc theo chuyên môn của nhân viên cho từng sản phẩm cụ thể.  
* Cung cấp hệ thống quản lý KPI nhân viên và xác định ca làm việc rõ ràng.  
* Tổng hợp và báo cáo nhu cầu khách hàng về sản phẩm.  
* Hạn chế quyền truy cập dữ liệu tin nhắn khách hàng, vì tất cả nhân viên đều hoạt động thông qua một tài khoản OA chung.  
  **Giải pháp:**  
  Từ đó, nhóm chúng tôi đề xuất một hệ thống có khả năng giải quyết tất cả các vấn đề nêu trên, mang tên **OmniChat**.  
  OmniChat là hệ thống được thiết kế cho bộ phận quản lý và dịch vụ khách hàng của doanh nghiệp trên nhiều nền tảng mạng xã hội. Giải pháp này tập trung tất cả tin nhắn từ các kênh khác nhau vào một nơi duy nhất, đồng thời tích hợp quản lý quy trình kinh doanh, cung cấp một nền tảng thống nhất và hiệu quả cho tổ chức.  
  **Giải pháp bao gồm:**  
* Xem và phản hồi tin nhắn khách hàng từ tất cả các nền tảng trong một giao diện thống nhất, với mọi thao tác được thực hiện qua một quy trình duy nhất.  
* Cung cấp khả năng phân tích nội dung tin nhắn bằng AI, bao gồm phát hiện từ khóa, để tạo dữ liệu hỗ trợ hoạt động và quy trình nội bộ của doanh nghiệp.  
* Cung cấp hệ thống quản lý nhân sự toàn diện, bao gồm quản lý thời gian làm việc, quản lý từ khóa quan trọng, và quản lý thông tin khách hàng trong cùng một ứng dụng.  
* Tích hợp phân công công việc tự động, cho phép doanh nghiệp phân bổ nhiệm vụ dựa trên chuyên môn nhân viên theo từ khóa tin nhắn khách hàng, KPI và các tiêu chí vận hành khác.  
* Cung cấp bảng điều khiển toàn diện hiển thị các thông tin chính như khối lượng tin nhắn hàng ngày, nhu cầu tư vấn khách hàng, và chỉ số hiệu suất nhân viên bao gồm mục tiêu hàng tháng.  
  **Yêu cầu chức năng:**  
   Các tính năng chính:  
* Cho phép nhận và phản hồi tương tác từ các nền tảng bên thứ ba (như Zalo OA, Facebook, Instagram) thông qua tích hợp API. Việc trao đổi dữ liệu và giao tiếp với máy chủ đối tác được tự động hóa theo thời gian thực qua cơ chế Webhook, đảm bảo đồng bộ và chính xác.  
* Phân tích nội dung tin nhắn để xác định từ khóa bằng AI, lưu trữ dữ liệu tin nhắn nhằm mục đích tổng hợp và báo cáo nhu cầu khách hàng.  
* Tích hợp các tính năng quản lý nhân sự, bao gồm theo dõi thời gian làm việc của nhân viên, quản lý KPI, quản lý từ khóa dịch vụ quan trọng và các yêu cầu vận hành đặc thù của doanh nghiệp.  
* Tích hợp phân công công việc tự động dựa trên thuật toán phân tích từ khóa, trích xuất từ khóa quan trọng từ tin nhắn khách hàng để xác định nhân viên phụ trách tư vấn phù hợp. Việc phân bổ nhiệm vụ được tối ưu thêm theo KPI và trạng thái làm việc thực tế của từng phòng ban.  
* Hệ thống sử dụng dữ liệu thu thập từ các nền tảng tích hợp để tạo báo cáo thống kê tóm tắt xu hướng tương tác khách hàng, khối lượng tin nhắn, và chỉ số hiệu suất nhân viên trong các kỳ báo cáo do doanh nghiệp quy định.  
  **OmniChat sẽ hỗ trợ các vai trò sau cùng chức năng tương ứng:**  
* **Nhân viên (Staff) – ứng dụng di động & web:**

  * Nhận thông báo về tin nhắn hoặc yêu cầu tư vấn từ khách hàng qua tài khoản OA của doanh nghiệp.  
  * Đánh dấu yêu cầu là “Hoàn thành” sau khi hỗ trợ và tư vấn khách hàng.  
  * Tạo các biểu mẫu yêu cầu nội bộ như xin nghỉ phép, tăng lương, và các biểu mẫu tương tự.  
  * Nhận thông báo khi yêu cầu được quản lý phê duyệt hoặc từ chối.  
  * Xem thông tin cơ bản của khách hàng như số điện thoại, email, tên và các chi tiết liên quan.  
  * Theo dõi thông tin cá nhân và dữ liệu hiệu suất của bản thân.  
* **Quản lý (Manager) – ứng dụng di động & web:**

  * Tạo, cập nhật, xóa và giám sát thông tin của tất cả nhân viên trong phòng ban.  
  * Tạo, cập nhật, xóa và giám sát thống kê KPI của phòng ban.  
  * Tạo, cập nhật, xóa và giám sát danh sách từ khóa được sử dụng trong phòng ban.  
  * Xem xét và phê duyệt hoặc từ chối tất cả yêu cầu do nhân viên gửi.  
  * Tạo, cập nhật, xóa và giám sát ca làm việc và lịch làm việc của nhân viên.  
  * Phân công ca làm việc cho nhân viên.  
* **Quản trị viên (Admin) – ứng dụng di động & web:**

  * Xem thống kê theo nhiều chiều dữ liệu: theo phòng ban, theo nhân viên (Staff/Manager), theo loại yêu cầu, theo khoảng thời gian.  
  * Xem danh sách tất cả từ khóa do các quản lý phòng ban tạo trong hệ thống.  
  * Quản lý tài khoản của nhân viên và quản lý.  
  * Phân công hoặc chuyển đổi quyền giữa Staff ↔ Manager.

  **Yêu cầu phi chức năng:**

* Hiệu năng: Hệ thống phải xử lý đồng thời 1000 người dùng mà không gặp vấn đề về hiệu suất.  
* Bảo mật: Hệ thống phải áp dụng cơ chế xác thực và phân quyền bằng JWT; mã hóa dữ liệu nhạy cảm; bảo vệ kênh giao tiếp của hệ thống chat bằng HTTPS/TLS; ngăn chặn các lỗ hổng bảo mật phổ biến như XSS và SQL Injection; và bảo vệ dữ liệu người dùng.  
* Khả năng sử dụng: Hệ thống phải cung cấp giao diện trực quan, dễ sử dụng cho Web App  
* Khả năng tương tác: Hệ thống phải tích hợp chặt chẽ và liền mạch với các API bên thứ ba như Zalo OA API, Meta Business Manager API, v.v.  
* Độ tin cậy: Hệ thống phải đảm bảo thời gian hoạt động tối thiểu 99,5% với cơ chế sao lưu và phục hồi dữ liệu hiệu quả.  
    
   Hệ thống phải được xây dựng theo kiến trúc clean architecture.  
* **Công nghệ phía Server:**  
  * Ngôn ngữ & Framework: Python Web API (hiệu năng cao, hệ sinh thái phong phú, đa nền tảng).  
  * Cơ sở dữ liệu: PostgreSQL.  
* **Công nghệ phía Client:**  
  * Web App: Next.js / React (framework hiện đại, mạnh mẽ cho hệ thống dashboard quản trị).  
* **Dịch vụ bên thứ ba:**  
  * Xác thực: Hệ thống tùy chỉnh sử dụng Python Identity & JWT.  
  * Triển khai: Microsoft Azure hoặc Google Cloud Platform.