import Foundation
import FoundationModels

struct Request: Decodable {
    let text: String
    let prompt: String?
    let maxTokens: Int?
}

struct Response: Encodable {
    let ok: Bool
    let output: String?
    let error: String?
    let availability: String
    let elapsed: Double
}

func availabilityString(_ availability: SystemLanguageModel.Availability) -> String {
    switch availability {
    case .available:
        return "available"
    case .unavailable(let reason):
        switch reason {
        case .deviceNotEligible:
            return "deviceNotEligible"
        case .appleIntelligenceNotEnabled:
            return "appleIntelligenceNotEnabled"
        case .modelNotReady:
            return "modelNotReady"
        @unknown default:
            return "unknownUnavailable"
        }
    @unknown default:
        return "unknown"
    }
}

func emit(_ response: Response) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    do {
        let data = try encoder.encode(response)
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    } catch {
        let fallback = #"{"ok":false,"output":null,"error":"jsonEncodeFailed","availability":"unknown","elapsed":0}"#
        FileHandle.standardOutput.write(Data(fallback.utf8))
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
}

@main
struct AppleLocalLLM {
    static func main() async {
        let started = Date()
        let model = SystemLanguageModel(useCase: .general, guardrails: .permissiveContentTransformations)
        let availability = availabilityString(model.availability)

        if CommandLine.arguments.contains("--check") {
            emit(Response(
                ok: model.isAvailable,
                output: nil,
                error: model.isAvailable ? nil : availability,
                availability: availability,
                elapsed: Date().timeIntervalSince(started)
            ))
            return
        }

        guard model.isAvailable else {
            emit(Response(
                ok: false,
                output: nil,
                error: availability,
                availability: availability,
                elapsed: Date().timeIntervalSince(started)
            ))
            return
        }

        let inputData = FileHandle.standardInput.readDataToEndOfFile()
        guard !inputData.isEmpty else {
            emit(Response(
                ok: false,
                output: nil,
                error: "emptyInput",
                availability: availability,
                elapsed: Date().timeIntervalSince(started)
            ))
            return
        }

        do {
            let request = try JSONDecoder().decode(Request.self, from: inputData)
            let text = request.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !text.isEmpty else {
                emit(Response(
                    ok: true,
                    output: "",
                    error: nil,
                    availability: availability,
                    elapsed: Date().timeIntervalSince(started)
                ))
                return
            }

            let instructions = """
            你是繁體中文語音輸入校正器。你的任務只限於：補標點、修明顯錯字、調整斷句、轉成台灣繁體中文。
            嚴格禁止刪除、摘要、合併、改寫或新增任何資訊。
            專有名詞、品牌、姓名、機器名稱、清單項目必須逐一保留；不確定的詞也必須保留原字。
            已存在的句號、問號、驚嘆號與段落斷點必須保留或等價轉換，不可移除。
            不要把口語改成正式報告，不要改變使用者原本語氣。
            只輸出一行或多行校正後文字。不得輸出「原文」、「校正後文字」、Markdown code fence 或任何說明。
            """
            let session = LanguageModelSession(model: model, instructions: instructions)
            let prompt = """
            校正這段語音辨識文字；只回傳校正後文字，不要加標籤、引號或 Markdown：
            \(text)
            """
            let options = GenerationOptions(
                sampling: .greedy,
                temperature: 0.0,
                maximumResponseTokens: request.maxTokens ?? 700
            )
            let response = try await session.respond(to: prompt, options: options)
            emit(Response(
                ok: true,
                output: response.content.trimmingCharacters(in: .whitespacesAndNewlines),
                error: nil,
                availability: availability,
                elapsed: Date().timeIntervalSince(started)
            ))
        } catch {
            emit(Response(
                ok: false,
                output: nil,
                error: String(describing: error),
                availability: availability,
                elapsed: Date().timeIntervalSince(started)
            ))
        }
    }
}
