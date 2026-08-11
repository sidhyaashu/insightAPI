"use client"

import { useState, FormEvent } from "react"
import { Bot, Zap, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    ChatBubble,
    ChatBubbleAvatar,
    ChatBubbleMessage,
} from "@/components/ui/chat-bubble"
import { ChatInput } from "@/components/ui/chat-input"
import {
    ExpandableChat as ExpandableChatPrimitive,
    ExpandableChatHeader,
    ExpandableChatBody,
    ExpandableChatFooter,
} from "@/components/ui/expandable-chat"
import { ChatMessageList } from "@/components/ui/chat-message-list"

export function ExpandableChatWidget() {
    const [messages, setMessages] = useState([
        {
            id: 1,
            content: "Welcome to InsightAPI AI! ⚡ How can I assist you with autonomous web API discovery or OpenAPI exports today?",
            sender: "ai",
        },
        {
            id: 2,
            content: "How does the zero-dependency Python SDK work?",
            sender: "user",
        },
        {
            id: 3,
            content: "You can import `insightapi` as a pure Python library! It runs in-memory without Postgres dependencies, making it perfect for CI/CD pipelines.",
            sender: "ai",
        },
    ])

    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        if (!input.trim()) return

        const userMsg = input
        setMessages((prev) => [
            ...prev,
            {
                id: prev.length + 1,
                content: userMsg,
                sender: "user",
            },
        ])
        setInput("")
        setIsLoading(true)

        setTimeout(() => {
            let aiReply = "InsightAPI autonomously explores web apps, extracts accessibility tree DOM snapshots, filters destructive actions, and generates OpenAPI 3.1 & Postman specifications."
            if (userMsg.toLowerCase().includes("pricing") || userMsg.toLowerCase().includes("cost")) {
                aiReply = "We offer a Free Tier (1 crawl/day), Starter ($29/mo), Pro ($99/mo), and Enterprise ($499/mo) with self-hosted Docker support."
            } else if (userMsg.toLowerCase().includes("sdk") || userMsg.toLowerCase().includes("python")) {
                aiReply = "Run `pip install insightapi` to use our Python SDK. Check out the technical docs for full API reference."
            }

            setMessages((prev) => [
                ...prev,
                {
                    id: prev.length + 1,
                    content: aiReply,
                    sender: "ai",
                },
            ])
            setIsLoading(false)
        }, 800)
    }

    return (
        <ExpandableChatPrimitive
            size="lg"
            position="bottom-right"
            className="fixed z-50"
            icon={<Zap className="h-6 w-6 text-white fill-white" />}
        >
            <ExpandableChatHeader className="flex-col text-center justify-center bg-muted/40">
                <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-orange-500 fill-orange-500" />
                    <h3 className="text-base font-bold text-foreground">InsightAPI AI Assistant ✨</h3>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                    Ask anything about autonomous API discovery & OpenAPI generation
                </p>
            </ExpandableChatHeader>

            <ExpandableChatBody>
                <ChatMessageList>
                    {messages.map((message) => (
                        <ChatBubble
                            key={message.id}
                            variant={message.sender === "user" ? "sent" : "received"}
                        >
                            <ChatBubbleAvatar
                                className="h-8 w-8 shrink-0 border border-border"
                                fallback={message.sender === "user" ? "YOU" : "AI"}
                            />
                            <ChatBubbleMessage
                                variant={message.sender === "user" ? "sent" : "received"}
                            >
                                {message.content}
                            </ChatBubbleMessage>
                        </ChatBubble>
                    ))}
                    {isLoading && (
                        <ChatBubble variant="received">
                            <ChatBubbleAvatar className="h-8 w-8 shrink-0" fallback="AI" />
                            <ChatBubbleMessage isLoading />
                        </ChatBubble>
                    )}
                </ChatMessageList>
            </ExpandableChatBody>

            <ExpandableChatFooter>
                <form onSubmit={handleSubmit} className="relative flex items-center w-full gap-2">
                    <ChatInput
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about InsightAPI..."
                        className="pr-12 min-h-[44px] h-[44px] py-2 text-xs"
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault()
                                handleSubmit(e)
                            }
                        }}
                    />
                    <Button
                        type="submit"
                        size="icon"
                        className="absolute right-2 h-8 w-8 bg-orange-500 hover:bg-orange-600 text-white cursor-pointer"
                        disabled={!input.trim() || isLoading}
                    >
                        <Send className="h-3.5 w-3.5" />
                    </Button>
                </form>
            </ExpandableChatFooter>
        </ExpandableChatPrimitive>
    )
}
