import React, { useState } from 'react';
import { Contact2, Mail, MessageSquare, Send, Phone, MapPin, Clock, Globe, HelpCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/PageHeader';

function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Create mailto link with form data
    const mailtoLink = `mailto:contact@evelina.bot?subject=${encodeURIComponent(formData.subject)}&body=${encodeURIComponent(
      `Name: ${formData.name}\nEmail: ${formData.email}\n\nMessage:\n${formData.message}`
    )}`;

    // Open default email client
    window.location.href = mailtoLink;

    // Show success message
    toast.custom((t) => (
      <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} max-w-md w-full bg-dark-2 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}>
        <div className="flex-1 w-0 p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0 pt-0.5">
              <Send className="h-10 w-10 text-green-500 p-2" />
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-100">Opening email client</p>
              <p className="mt-1 text-sm text-gray-400">Your message will be sent through your default email application.</p>
            </div>
          </div>
        </div>
        <div className="flex border-l border-dark-4">
          <button onClick={() => toast.dismiss(t.id)} className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-green-500 hover:text-green-400 focus:outline-none">
            Close
          </button>
        </div>
      </div>
    ), { position: "top-right", duration: 3000 });

    // Reset form
    setFormData({
      name: '',
      email: '',
      subject: '',
      message: ''
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <PageHeader
        icon={<Contact2 />}
        title="Contact Support"
        description="Get in touch with our support team"
      />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <HelpCircle className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Get in Touch</h2>
          </div>
          
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
                <Mail className="w-6 h-6 text-theme" />
              </div>
              <div>
                <h3 className="font-medium">Email Support</h3>
                <a href="mailto:contact@evelina.bot" className="text-theme hover:text-theme/80">
                  contact@evelina.bot
                </a>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
                <MessageSquare className="w-6 h-6 text-theme" />
              </div>
              <div>
                <h3 className="font-medium">Discord Support</h3>
                <a 
                  href="https://discord.gg/evelina" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-theme hover:text-theme/80"
                >
                  Join our Discord Server
                </a>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
                <Clock className="w-6 h-6 text-theme" />
              </div>
              <div>
                <h3 className="font-medium">Response Time</h3>
                <p className="text-gray-400">Within 24 hours</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
                <Globe className="w-6 h-6 text-theme" />
              </div>
              <div>
                <h3 className="font-medium">Languages</h3>
                <p className="text-gray-400">English, German</p>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-theme/10 flex items-center justify-center">
              <Send className="w-6 h-6 text-theme" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Send a Message</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-400 mb-1">
                Name
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-lg bg-dark-2 border border-dark-4 focus:outline-none focus:ring-2 focus:ring-theme text-white"
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-400 mb-1">
                Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-lg bg-dark-2 border border-dark-4 focus:outline-none focus:ring-2 focus:ring-theme text-white"
                required
              />
            </div>

            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-gray-400 mb-1">
                Subject
              </label>
              <input
                type="text"
                id="subject"
                name="subject"
                value={formData.subject}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-lg bg-dark-2 border border-dark-4 focus:outline-none focus:ring-2 focus:ring-theme text-white"
                required
              />
            </div>

            <div>
              <label htmlFor="message" className="block text-sm font-medium text-gray-400 mb-1">
                Message
              </label>
              <textarea
                id="message"
                name="message"
                value={formData.message}
                onChange={handleChange}
                rows={6}
                className="w-full px-4 py-2 rounded-lg bg-dark-2 border border-dark-4 focus:outline-none focus:ring-2 focus:ring-theme text-white resize-none"
                required
              />
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-theme to-theme/80 hover:from-theme/90 hover:to-theme/70 text-white px-6 py-3 rounded-lg font-medium transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-theme/20 flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send Message
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Contact;